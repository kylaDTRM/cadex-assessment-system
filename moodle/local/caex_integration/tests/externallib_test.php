<?php
use advanced_testcase;

defined('MOODLE_INTERNAL') || die();

class local_caex_integration_externallib_test extends advanced_testcase {

    protected function setUp(): void {
        $this->resetAfterTest(true);
    }

    public function test_get_capabilities_structure() {
        $cap = \local_caex_integration\externallib::get_capabilities();
        $this->assertIsArray($cap);
        $this->assertArrayHasKey('enabled', $cap);
        $this->assertArrayHasKey('capabilities', $cap);
        $this->assertArrayHasKey('server_time', $cap);
    }

}
