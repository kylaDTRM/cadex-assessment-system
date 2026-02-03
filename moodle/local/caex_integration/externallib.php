<?php
namespace local_caex_integration;

defined('MOODLE_INTERNAL') || die();

use external_function_parameters;
use external_value;
use external_single_structure;
use external_multiple_structure;
use external_api;
use coreormat_text;

require_once($CFG->libdir . "/externallib.php");

class externallib extends \external_api {

    public static function update_grade_parameters() {
        return new external_function_parameters([
            'itemid' => new external_value(PARAM_INT, 'The grade item id'),
            'userid' => new external_value(PARAM_INT, 'The Moodle user id'),
            'grade'  => new external_value(PARAM_RAW, 'Grade value (string/float)'),
            'timestamp' => new external_value(PARAM_TEXT, 'ISO8601 timestamp of grading event'),
            'client_request_id' => new external_value(PARAM_TEXT, 'Client idempotency key')
        ]);
    }

    public static function update_grade($itemid, $userid, $grade, $timestamp, $client_request_id='') {
        global $DB, $USER;

        $params = self::validate_parameters(self::update_grade_parameters(), [
            'itemid' => $itemid,
            'userid' => $userid,
            'grade' => $grade,
            'timestamp' => $timestamp,
            'client_request_id' => $client_request_id
        ]);

        // Capability check.
        $context = \context_system::instance();
        require_capability('local/caex_integration:manage', $context);

        // Idempotency: try to avoid duplicate application using a simple unique key table.
        // Minimal implementation (for illustration); plugin should create a proper table with indexes.
        $existing = $DB->get_record('local_caex_ops', ['client_request_id' => $client_request_id], '*', IGNORE_MISSING);
        if ($client_request_id && $existing) {
            return ['status' => 'already_applied', 'operation_id' => $existing->id];
        }

        // Validate grade item and user existence.
        $gradeitem = $DB->get_record('grade_items', ['id' => $itemid], '*', MUST_EXIST);
        $user = $DB->get_record('user', ['id' => $userid], '*', MUST_EXIST);

        // Apply grade with transactional safety and validation.
        $transaction = $DB->start_delegated_transaction();
        try {
            $gradeitem = $DB->get_record('grade_items', ['id' => $itemid], '*', MUST_EXIST);

            // Validate numeric grade if grade type is numeric.
            if ($gradeitem->gradetype == GRADE_TYPE_VALUE) {
                if (!is_numeric($grade)) {
                    throw new \invalid_parameter_exception('Grade must be numeric for this grade item');
                }
                $numgrade = (float)$grade;
                if ($gradeitem->grademax !== null && $numgrade > $gradeitem->grademax) {
                    throw new \invalid_parameter_exception('Grade exceeds maximum');
                }
            } else {
                // for other grade types, accept string and rely on Moodle validation.
                $numgrade = $grade;
            }

            // Use grade_update properly: prepare an array of grade items.
            $grades = [];
            $g = new \stdClass();
            $g->itemid = $itemid;
            $g->userid = $userid;
            $g->rawgrade = $numgrade;
            $grades[$itemid] = $g;

            // grade_update expects: array of grade item objects
            grade_update('\', $grades);

            // Persist operation record (requires DB table in install.xml)
            if ($client_request_id) {
                $record = new \stdClass();
                $record->client_request_id = $client_request_id;
                $record->type = 'grade_update';
                $record->payload = json_encode($params);
                $record->timecreated = time();
                $record->actor = $USER->id;
                $record->id = $DB->insert_record('local_caex_ops', $record);
            }

            $transaction->allow_commit();

            return ['status' => 'ok', 'operation_id' => $record->id ?? 0];
        } catch (\Exception $e) {
            // On any failure, rollback and report.
            $transaction->rollback($e);
            throw $e;
        }
    }

    public static function update_grade_returns() {
        return new external_single_structure([
            'status' => new external_value(PARAM_TEXT, 'status string'),
            'operation_id' => new external_value(PARAM_INT, 'operation id')
        ]);
    }

    public static function get_capabilities_parameters() {
        return new external_function_parameters([]);
    }

    public static function get_capabilities() {
        $context = \context_system::instance();
        // Return a simple status payload the external platform can use to verify connectivity and permissions.
        return [
            'enabled' => true,
            'capabilities' => ['manage' => has_capability('local/caex_integration:manage', $context)],
            'server_time' => date('c')
        ];
    }

    public static function get_capabilities_returns() {
        return new external_single_structure([
            'enabled' => new external_value(PARAM_BOOL, 'plugin enabled'),
            'capabilities' => new external_single_structure(['manage' => new external_value(PARAM_BOOL, 'manage')]),
            'server_time' => new external_value(PARAM_TEXT, 'server time ISO8601')
        ]);
    }
}
