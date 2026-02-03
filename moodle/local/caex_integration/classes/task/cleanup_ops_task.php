<?php
namespace local_caex_integration\task;

defined('MOODLE_INTERNAL') || die();

use core\task\scheduled_task;

class cleanup_ops_task extends scheduled_task {
    public function get_name() : string {
        return get_string('task_cleanup_ops', 'local_caex_integration');
    }

    public function execute() {
        global $DB;
        // Delete ops older than 90 days to bound table growth. Adjust as needed.
        $threshold = time() - (90 * 24 * 60 * 60);
        $DB->delete_records_select('local_caex_ops', 'timecreated < ?', [$threshold]);
    }
}
