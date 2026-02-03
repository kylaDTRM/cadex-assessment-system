<?php
defined('MOODLE_INTERNAL') || die();

/* Web service function descriptions. See https://docs.moodle.org/dev/Web_service_API */
$functions = [
    'local_caex_integration_update_grade' => [
        'classname'   => 'local_caex_integration\externallib',
        'methodname'  => 'update_grade',
        'classpath'   => '',
        'description' => 'Update a grade in Moodle gradebook (idempotent).',
        'type'        => 'write',
        'capabilities'=> 'local/caex_integration:manage'
    ],
    'local_caex_integration_get_capabilities' => [
        'classname'   => 'local_caex_integration\externallib',
        'methodname'  => 'get_capabilities',
        'classpath'   => '',
        'description' => 'Return plugin capabilities and status for external integration.',
        'type'        => 'read',
    ],
];

$services = [
    'CAEX integration service' => [
        'functions' => [
            'local_caex_integration_update_grade',
            'local_caex_integration_get_capabilities'
        ],
        'restrictedusers' => 0,
        'enabled' => 1,
    ],
];
