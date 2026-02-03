<?php
require_once(__DIR__ . '/../../config.php');
require_login();

$context = context_system::instance();
require_capability('local/caex_integration:manage', $context);

$id = required_param('id', PARAM_INT);
$sesskey = required_param('sesskey', PARAM_RAW);

if (!confirm_sesskey()) {
    print_error('badrequest', 'error');
}

global $DB;
$record = $DB->get_record('local_caex_webhooks', ['id' => $id], '*', MUST_EXIST);
$record->attempts = 0;
$DB->update_record('local_caex_webhooks', $record);

redirect(new moodle_url('/local/caex_integration/admin/webhooks.php'));
