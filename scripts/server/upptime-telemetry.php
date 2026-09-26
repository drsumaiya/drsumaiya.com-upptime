<?php
/**
 * Plugin Name: Upptime Telemetry & Views API
 * Description: Secure REST API endpoints for telemetry, page views, and popularity monitoring.
 * Version: 1.0.0
 * Author: Dr. Sumaiya
 */

if (!defined('ABSPATH')) {
    exit;
}

add_action('rest_api_init', function () {
    register_rest_route('upptime/v1', '/page-views', [
        'methods' => 'GET',
        'callback' => 'upptime_get_page_views',
        'permission_callback' => 'upptime_verify_telemetry_token',
        'args' => [
            'days' => [
                'type' => 'integer',
                'default' => 1,
                'sanitize_callback' => 'absint',
            ],
            'limit' => [
                'type' => 'integer',
                'default' => 50,
                'sanitize_callback' => 'absint',
            ],
            'date' => [
                'type' => 'string',
                'sanitize_callback' => 'sanitize_text_field',
            ],
        ],
    ]);
});

function upptime_verify_telemetry_token($request)
{
    // Prevent LiteSpeed and browser/proxy caching of telemetry responses
    if (!defined('DONOTCACHEPAGE')) {
        define('DONOTCACHEPAGE', true);
    }
    if (!headers_sent()) {
        header('X-LiteSpeed-Cache-Control: no-cache');
        header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
        header('Pragma: no-cache');
    }

    // Read secret strictly from server-side private wp-config.php or environment variable.
    // Secrets must NEVER be committed to the public Git repository.
    $expected_token = defined('UPPTIME_TELEMETRY_SECRET')
        ? UPPTIME_TELEMETRY_SECRET
        : (defined('UPPTIME_WAF_SECRET') ? UPPTIME_WAF_SECRET : (getenv('UPPTIME_WAF_SECRET') ?: ''));

    if (empty($expected_token)) {
        return new WP_Error(
            'rest_forbidden',
            'Telemetry error: UPPTIME_TELEMETRY_SECRET constant is not configured in origin wp-config.php.',
            ['status' => 500]
        );
    }

    // Check X-Upptime-Token header
    $token = $request->get_header('x_upptime_token');
    if (empty($token) && isset($_SERVER['HTTP_X_UPPTIME_TOKEN'])) {
        $token = $_SERVER['HTTP_X_UPPTIME_TOKEN'];
    }

    // Check Authorization: Bearer <token>
    if (empty($token)) {
        $auth_header = $request->get_header('authorization');
        if (!empty($auth_header) && preg_match('/Bearer\s+(\S+)/i', $auth_header, $matches)) {
            $token = $matches[1];
        }
    }

    // Check query parameter ?token=<token>
    if (empty($token)) {
        $token = $request->get_param('token');
    }

    if (!empty($token) && hash_equals($expected_token, (string) $token)) {
        return true;
    }

    return new WP_Error(
        'rest_forbidden',
        'Access denied: Invalid or missing telemetry authentication token.',
        ['status' => 403]
    );
}

function upptime_get_page_views($request)
{
    $days = (int) $request->get_param('days');
    if ($days < 1) {
        $days = 1;
    }
    if ($days > 90) {
        $days = 90;
    }

    $limit = (int) $request->get_param('limit');
    if ($limit < 1) {
        $limit = 50;
    }
    if ($limit > 200) {
        $limit = 200;
    }

    $date = $request->get_param('date');

    if (!function_exists('stats_get_csv')) {
        $stats_module = WP_CONTENT_DIR . '/plugins/jetpack/modules/stats.php';
        if (file_exists($stats_module)) {
            require_once $stats_module;
        }
    }

    if (!function_exists('stats_get_csv')) {
        return new WP_Error(
            'stats_unavailable',
            'Jetpack stats engine is not accessible on this host.',
            ['status' => 500]
        );
    }

    $csv_args = [
        'days' => $days,
        'limit' => $limit,
    ];
    if (!empty($date)) {
        $csv_args['date'] = $date;
    }

    $raw_posts = stats_get_csv('postviews', $csv_args);
    $total_views_data = stats_get_csv('views', ['days' => $days]);

    $total_views = 0;
    if (!empty($total_views_data) && isset($total_views_data[0]['views'])) {
        $total_views = (int) $total_views_data[0]['views'];
    }

    $items = [];
    if (is_array($raw_posts)) {
        foreach ($raw_posts as $row) {
            $post_id = isset($row['post_id']) ? (int) $row['post_id'] : 0;
            $views = isset($row['views']) ? (int) $row['views'] : 0;
            $title = isset($row['post_title']) ? html_entity_decode(trim($row['post_title']), ENT_QUOTES, 'UTF-8') : '';
            $permalink = isset($row['post_permalink']) ? trim($row['post_permalink']) : '';

            $post_type = 'other';
            if ($post_id > 0) {
                $type = get_post_type($post_id);
                if ($type) {
                    $post_type = $type;
                }
            } elseif ($post_id === 0) {
                $post_type = 'home';
            }

            if ($post_id === 0 && empty($title)) {
                $title = 'Home page';
            }

            $items[] = [
                'post_id' => $post_id,
                'title' => $title,
                'url' => $permalink,
                'type' => $post_type,
                'views' => $views,
            ];
        }
    }

    return rest_ensure_response([
        'status' => 'ok',
        'site' => get_bloginfo('name'),
        'site_url' => home_url('/'),
        'timestamp' => current_time('mysql', true),
        'days_queried' => $days,
        'total_views' => $total_views,
        'count' => count($items),
        'pages' => $items,
    ]);
}
