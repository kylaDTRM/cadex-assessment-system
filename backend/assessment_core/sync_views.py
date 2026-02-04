from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.utils import timezone
from .models import Attempt, Response as AttemptResponse, SyncLog, Question, Assessment
from .serializers import AttemptSerializer
import uuid


class SyncAttemptView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        payload = request.data
        client_id = payload.get('client_id')
        base_version = payload.get('base_version')
        attempt_payload = payload.get('attempt', {})
        responses = payload.get('responses', [])

        # Use authenticated user as student
        student = request.user

        # Find existing attempt by client_id or create new
        attempt = None
        if client_id:
            try:
                uuid.UUID(client_id)
            except Exception:
                return Response({'error': 'invalid client_id'}, status=status.HTTP_400_BAD_REQUEST)
            attempt = Attempt.objects.filter(client_id=client_id, student=student).first()

        if not attempt:
            # create new attempt
            try:
                assessment_id = attempt_payload.get('assessment_id')
                assessment = Assessment.objects.get(id=assessment_id)
            except Exception:
                return Response({'error': 'invalid assessment_id'}, status=status.HTTP_400_BAD_REQUEST)

            attempt = Attempt.objects.create(
                assessment=assessment,
                student=student,
                attempt_number=attempt_payload.get('attempt_number', 1),
                client_id=client_id or uuid.uuid4(),
                client_version=attempt_payload.get('client_version', 0),
                server_version=1,
                status=attempt_payload.get('status', 'IN_PROGRESS'),
                last_client_ts=attempt_payload.get('last_client_ts', None)
            )

            # create responses
            for r in responses:
                try:
                    q = Question.objects.get(id=r['question_id'])
                except Exception:
                    continue
                AttemptResponse.objects.create(attempt=attempt, question=q, response_data=r.get('answer', {}))

            # Log sync
            SyncLog.objects.create(resource_type='attempt', resource_client_id=attempt.client_id, operation='create', payload=payload, client_ts=attempt.last_client_ts, client_id=str(client_id))

            return Response({'server_id': str(attempt.id), 'server_version': attempt.server_version}, status=status.HTTP_201_CREATED)

        # Existing attempt — check version
        if base_version is not None and base_version != attempt.server_version:
            # conflict — return server state and conflict fields
            data = AttemptSerializer(attempt).data
            return Response({'detail': 'version conflict', 'server_state': data, 'server_version': attempt.server_version}, status=status.HTTP_409_CONFLICT)

        # Apply updates
        changed = False
        if 'status' in attempt_payload:
            attempt.status = attempt_payload['status']
            changed = True
        if 'submitted_at' in attempt_payload:
            attempt.submitted_at = attempt_payload['submitted_at']
            changed = True
        if 'client_version' in attempt_payload:
            attempt.client_version = attempt_payload['client_version']
            changed = True
        attempt.last_client_ts = attempt_payload.get('last_client_ts', attempt.last_client_ts)

        # upsert responses by question
        for r in responses:
            qid = r.get('question_id')
            try:
                q = Question.objects.get(id=qid)
            except Exception:
                continue
            resp_obj = AttemptResponse.objects.filter(attempt=attempt, question=q).first()
            if resp_obj:
                resp_obj.response_data = r.get('answer', resp_obj.response_data)
                resp_obj.answered_at = timezone.now()
                resp_obj.save()
            else:
                AttemptResponse.objects.create(attempt=attempt, question=q, response_data=r.get('answer', {}))
            changed = True

        if changed:
            attempt.server_version += 1
            attempt.save()
            SyncLog.objects.create(resource_type='attempt', resource_client_id=attempt.client_id, operation='update', payload=payload, client_ts=attempt.last_client_ts, client_id=str(client_id))

        return Response({'server_id': str(attempt.id), 'server_version': attempt.server_version})


class SyncChangesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        since = request.query_params.get('since')
        qs = SyncLog.objects.all().order_by('timestamp')
        if since:
            try:
                # treat since as ISO timestamp
                since_ts = timezone.datetime.fromisoformat(since)
                qs = qs.filter(timestamp__gt=since_ts)
            except Exception:
                pass
        items = []
        for s in qs[:100]:
            items.append({'resource_type': s.resource_type, 'resource_client_id': str(s.resource_client_id) if s.resource_client_id else None, 'operation': s.operation, 'payload': s.payload, 'timestamp': s.timestamp.isoformat()})
        return Response({'changes': items})


class SyncAckView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        body = request.data
        server_id = body.get('server_id')
        server_version = body.get('server_version')
        if not server_id:
            return Response({'error': 'server_id required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            attempt = Attempt.objects.get(id=server_id)
        except Attempt.DoesNotExist:
            return Response({'error': 'unknown server_id'}, status=status.HTTP_400_BAD_REQUEST)
        # If client provided a server_version, ensure it matches current server_version
        if server_version is not None and int(server_version) != attempt.server_version:
            data = AttemptSerializer(attempt).data
            return Response({'detail': 'version conflict', 'server_state': data, 'server_version': attempt.server_version}, status=status.HTTP_409_CONFLICT)
        # Mark as synced for this client
        attempt.status = 'SYNCED'
        attempt.save()
        return Response({'status': 'acknowledged'})
