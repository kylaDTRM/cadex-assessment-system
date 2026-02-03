<?php
namespace local_caex_integration\webhook;

defined('MOODLE_INTERNAL') || die();

class processor {
    /**
     * Enqueue webhook into local log and return id.
     * Actual delivery should be handled by a worker to allow retries and DLQs.
     */
    public static function enqueue($event, array $payload) {
        global $DB;
        $record = new \stdClass();
        $record->event = $event;
        $record->payload = json_encode($payload);
        $record->timecreated = time();
        $record->http_code = 0;
        $record->response = '';
        $record->attempts = 0;
        $record->id = $DB->insert_record('local_caex_webhooks', $record);
        return $record->id;
    }

    public static function process_next($maxattempts = 5) {
        global $DB;
        $record = $DB->get_record_select('local_caex_webhooks', 'attempts < ?', [$maxattempts], '*', IGNORE_MISSING);
        if (!$record) {
            return false;
        }
        // Look up plugin settings
        $apibase = get_config('local_caex_integration', 'api_base_url');
        $secret = get_config('local_caex_integration', 'shared_secret');
        if (!$apibase || !$secret) {
            // cannot dispatch
            return false;
        }
        $payload = json_decode($record->payload, true);
        try {
            $res = forwarder::send_event($apibase . '/api/v1/webhooks', $secret, $payload);
            $record->http_code = $res['http_code'];
            $record->response = $res['body'];
            $record->attempts += 1;
            $DB->update_record('local_caex_webhooks', $record);
            return true;
        } catch (\Exception $e) {
            $record->attempts += 1;
            $record->response = $e->getMessage();
            $DB->update_record('local_caex_webhooks', $record);
            return false;
        }
    }
}
