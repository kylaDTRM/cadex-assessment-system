<?php
namespace local_caex_integration\webhook;

defined('MOODLE_INTERNAL') || die();

class forwarder {

    /**
     * Send an event to external API with HMAC-SHA256 signing.
     * @param string $url
     * @param string $secret
     * @param array $payload
     * @return array ['http_code'=>int, 'body'=>string]
     */
    public static function send_event($url, $secret, array $payload) {
        $json = json_encode($payload);
        $timestamp = gmdate('c');
        $signature_payload = $timestamp . '.' . $json;
        $signature = hash_hmac('sha256', $signature_payload, $secret);

        $headers = [
            'Content-Type: application/json',
            'X-Timestamp: ' . $timestamp,
            'X-Signature: sha256=' . $signature
        ];

        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $json);
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
        // Consider CURLOPT_TIMEOUT, CURLOPT_SSL_VERIFYHOST, etc. in production.

        $body = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $err = curl_error($ch);
        curl_close($ch);

        if ($err) {
            throw new \Exception('Webhook forward failed: ' . $err);
        }

        return ['http_code' => $code, 'body' => $body];
    }
}
