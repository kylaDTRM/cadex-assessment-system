<?php
namespace local_caex_integration\task;

defined('MOODLE_INTERNAL') || die();

use core\task\scheduled_task;

class process_webhooks_task extends scheduled_task {
    public function get_name() : string {
        return get_string('task_process_webhooks', 'local_caex_integration');
    }

    public function execute() {
        // Process up to N webhooks per run to avoid long-running tasks.
        $max = 50;
        $processed = 0;
        while ($processed < $max) {
            $ok = \local_caex_integration\webhook\processor::process_next();
            if (!$ok) {
                break;
            }
            $processed++;
        }
    }
}
