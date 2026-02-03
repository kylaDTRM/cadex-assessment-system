<?php
namespace local_caex_integration\cli;

defined('MOODLE_INTERNAL') || die();

use cli;

class reconcile {
    /**
     * Entry-point for CLI reconciliation stub.
     * This should be invoked by cron or admin CLI to run a full reconciliation job (makes API calls to external platform).
     */
    public static function run() {
        global $CFG;

        cli::writeln("Starting CAEX reconciliation (stub)...");
        // TODO: implement reconciliation logic: fetch mappings, compare enrolments, enqueue sync jobs.

        cli::writeln("Completed (stub). Implement reconciliation logic in classes/sync/* and tasks.");
    }
}
