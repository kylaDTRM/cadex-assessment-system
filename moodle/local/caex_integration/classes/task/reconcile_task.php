<?php
namespace local_caex_integration\task;

defined('MOODLE_INTERNAL') || die();

use core\task\scheduled_task;

class reconcile_task extends scheduled_task {
    public function get_name() : string {
        return get_string('task_reconcile', 'local_caex_integration');
    }

    public function execute() {
        // Delegate to CLI reconciliation stub.
        \local_caex_integration\cli\reconcile::run();
    }
}
