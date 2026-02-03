<?php
/**
 * Simple admin test endpoint for the CAEX plugin.
 * POST JSON: {"action":"ping"}  -> returns {status: "ok", server_time: "..."}
 * Requires: logged-in user with 'local/caex_integration:manage'
 */

require_once(__DIR__ . '/../../config.php');
require_login();

$context = context_system::instance();
require_capability('local/caex_integration:manage', $context);

$payload = json_decode(file_get_contents('php://input'), true) ?: [];
$action = $payload['action'] ?? optional_param('action', '', PARAM_TEXT);

header('Content-Type: application/json');

if ($action === 'ping') {
    echo json_encode(['status' => 'ok', 'server_time' => date('c')]);
    exit;
}

if ($action === 'test_update_grade') {
    // Useful for manual testing: pass itemid, userid, grade, client_request_id
    $itemid = $payload['itemid'] ?? 0;
    $userid = $payload['userid'] ?? 0;
    $grade = $payload['grade'] ?? null;
    $client_request_id = $payload['client_request_id'] ?? uniqid('', true);

    try {
        $result = \local_caex_integration\externallib::update_grade($itemid, $userid, $grade, date('c'), $client_request_id);
        echo json_encode(['status' => 'ok', 'result' => $result]);
    } catch (Exception $e) {
        http_response_code(400);
        echo json_encode(['status' => 'error', 'message' => $e->getMessage()]);
    }
    exit;
}

http_response_code(400);
echo json_encode(['status' => 'error', 'message' => 'unknown action']);
exit;
