<?php
defined('MOODLE_INTERNAL') || die();

$capabilities = [
    'local/caex_integration:manage' => [
        'captype' => 'write',
        'contextlevel' => CONTEXT_SYSTEM,
        'archetypes' => [
            'manager' => CAP_ALLOW
        ]
    ],
];
