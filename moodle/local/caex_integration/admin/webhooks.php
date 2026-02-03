<?php
require_once(__DIR__ . '/../../config.php');
require_login();

$context = context_system::instance();
require_capability('local/caex_integration:manage', $context);

$PAGE->set_url(new moodle_url('/local/caex_integration/admin/webhooks.php'));
$PAGE->set_context($context);
$PAGE->set_title(get_string('webhooks', 'local_caex_integration'));
$PAGE->set_heading(get_string('webhooks', 'local_caex_integration'));

echo $OUTPUT->header();

// Simple table listing of recent webhooks and action buttons to requeue (set attempts to 0)
global $DB;
$records = $DB->get_records('local_caex_webhooks', null, 'timecreated DESC', '*', 0, 100);

echo html_writer::start_tag('table', ['class' => 'generaltable']);
echo html_writer::start_tag('thead');
echo html_writer::start_tag('tr');
foreach (['ID','Event','Attempts','HTTP','Created','Actions'] as $h) {
    echo html_writer::tag('th', $h);
}
echo html_writer::end_tag('tr');
echo html_writer::end_tag('thead');

foreach ($records as $r) {
    echo html_writer::start_tag('tr');
    echo html_writer::tag('td', $r->id);
    echo html_writer::tag('td', s($r->event));
    echo html_writer::tag('td', $r->attempts);
    echo html_writer::tag('td', $r->http_code ?: '-');
    echo html_writer::tag('td', userdate($r->timecreated));
    $requeueurl = new moodle_url('/local/caex_integration/admin/requeue.php', ['id' => $r->id, 'sesskey' => sesskey()]);
    echo html_writer::tag('td', html_writer::link($requeueurl, get_string('requeue', 'local_caex_integration')));
    echo html_writer::end_tag('tr');
}

echo html_writer::end_tag('table');

echo $OUTPUT->footer();
