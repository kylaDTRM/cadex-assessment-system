<?php
use advanced_testcase;

defined('MOODLE_INTERNAL') || die();

class local_caex_integration_webhook_processor_test extends advanced_testcase {
    protected function setUp(): void {
        $this->resetAfterTest(true);
    }

    public function test_enqueue_and_process() {
        global $DB;
        // Set config to dummy values
        set_config('api_base_url', 'http://127.0.0.1:9999', 'local_caex_integration');
        set_config('shared_secret', 'secret', 'local_caex_integration');

        $payload = ['event' => 'test.event', 'data' => ['x' => 1]];
        $id = \local_caex_integration\webhook\processor::enqueue('test.event', $payload);
        $this->assertGreaterThan(0, $id);

        // Processing will fail to send (no server) but should not throw; attempts should increment
        $res = \local_caex_integration\webhook\processor::process_next(1);
        $this->assertFalse($res);

        $record = $DB->get_record('local_caex_webhooks', ['id' => $id]);
        $this->assertEquals(1, $record->attempts);
    }
}
