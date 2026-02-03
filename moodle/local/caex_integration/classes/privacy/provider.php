<?php
namespace local_caex_integration\privacy;

defined('MOODLE_INTERNAL') || die();

use core_privacy\local\metadata\collection;
use core_privacy\local\request\writer;

class provider implements \core_privacy\local\metadata\provider, \core_privacy\local\request\plugin
t{
    /**
     * Return meta data about data stored.
     */
    public static function _get_metadata(collection $collection) : collection {
        // This plugin stores no personal data by itself — it only forwards events and uses Moodle core records.
        // If this changes, add the declarations here.
        return $collection;
    }

    public static function export_user_data(array $userids) {
        // Implement export hooks if plugin stores user data in its own tables.
        // For MVP, no per-user data is stored here; rely on core export.
        return;
    }

    public static function delete_data_for_users(array $useridlist) {
        // If plugin stores personal data, remove it here.
        return;
    }
}
