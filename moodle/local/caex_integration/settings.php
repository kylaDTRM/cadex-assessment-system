<?php
defined('MOODLE_INTERNAL') || die();

if ($hassiteconfig) {
    $settings = new admin_settingpage('local_caex_integration_settings', get_string('pluginname', 'local_caex_integration'));

    $settings->add(new admin_setting_configtext('local_caex_integration/api_base_url',
        get_string('api_base_url', 'local_caex_integration'),
        get_string('api_base_url_desc', 'local_caex_integration'), '', PARAM_URL));

    $settings->add(new admin_setting_configtext('local_caex_integration/shared_secret',
        get_string('shared_secret', 'local_caex_integration'),
        get_string('shared_secret_desc', 'local_caex_integration'), '', PARAM_TEXT));

    $settings->add(new admin_setting_configcheckbox('local_caex_integration/enable_webhooks',
        get_string('enable_webhooks', 'local_caex_integration'), '', 1));

    $ADMIN->add('localplugins', $settings);
}
