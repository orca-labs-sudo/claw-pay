<?php
/**
 * Plugin Name: claw-pay Gateway
 * Plugin URI:  https://clawpay.eu/woocommerce
 * Description: Accept x402 USDC payments from OpenClaw AI agents. Your shop earns automatically — you pay 3% only when you earn.
 * Version:     0.1.0
 * Author:      orca-labs
 * Author URI:  https://github.com/orca-labs-sudo
 * License:     GPL-2.0-or-later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain: claw-pay-gateway
 * Requires WC: 7.0
 */

defined('ABSPATH') || exit;

add_action('plugins_loaded', 'claw_pay_init_gateway');

function claw_pay_init_gateway() {
    if (!class_exists('WC_Payment_Gateway')) return;

    class WC_Claw_Pay_Gateway extends WC_Payment_Gateway {

        public function __construct() {
            $this->id                 = 'claw_pay';
            $this->icon               = 'https://clawpay.eu/claw-pay-logo.png';
            $this->has_fields         = false;
            $this->method_title       = 'claw-pay (x402 / USDC)';
            $this->method_description = 'Accept payments from OpenClaw AI agents via x402 protocol. USDC on Base L2. 3% commission — only when you earn.';

            $this->init_form_fields();
            $this->init_settings();

            $this->title       = $this->get_option('title');
            $this->description = $this->get_option('description');
            $this->facilitator = rtrim($this->get_option('facilitator_url', 'https://claw-pay.org'), '/');
            $this->seller_addr = $this->get_option('seller_address', '');

            add_action('woocommerce_update_options_payment_gateways_' . $this->id, [$this, 'process_admin_options']);
            add_action('woocommerce_api_claw_pay', [$this, 'handle_x402_request']);
        }

        public function init_form_fields() {
            $this->form_fields = [
                'enabled' => [
                    'title'   => 'Enable',
                    'type'    => 'checkbox',
                    'label'   => 'Enable claw-pay (x402 / USDC)',
                    'default' => 'yes',
                ],
                'title' => [
                    'title'   => 'Title',
                    'type'    => 'text',
                    'default' => 'Pay with USDC (AI Agent)',
                ],
                'description' => [
                    'title'   => 'Description',
                    'type'    => 'textarea',
                    'default' => 'Automatic USDC payment via OpenClaw AI agent (x402 protocol).',
                ],
                'seller_address' => [
                    'title'       => 'Your USDC Wallet Address (Base L2)',
                    'type'        => 'text',
                    'description' => 'Your Base L2 wallet — 97% of each payment lands here.',
                    'placeholder' => '0x...',
                ],
                'facilitator_url' => [
                    'title'   => 'Facilitator URL',
                    'type'    => 'text',
                    'default' => 'https://claw-pay.org',
                    'description' => 'Leave default unless you run your own facilitator.',
                ],
            ];
        }

        /**
         * Detect x402 payment header on REST / WC API calls.
         * Called via: /wc-api/claw_pay?order_id=123
         */
        public function handle_x402_request() {
            $order_id      = absint($_GET['order_id'] ?? 0);
            $payment_header = $_SERVER['HTTP_X_PAYMENT'] ?? $_SERVER['HTTP_PAYMENT_SIGNATURE'] ?? '';

            if (!$order_id) {
                wp_send_json(['error' => 'Missing order_id'], 400);
            }

            $order = wc_get_order($order_id);
            if (!$order) {
                wp_send_json(['error' => 'Order not found'], 404);
            }

            // No payment header → return 402 with requirements
            if (!$payment_header) {
                $this->send_payment_required($order);
            }

            // Has payment header → settle via facilitator
            $payment_data = json_decode(base64_decode($payment_header), true);
            if (!$payment_data) {
                wp_send_json(['error' => 'Invalid payment header'], 400);
            }

            $amount_usdc = (int) round($order->get_total() * 1_000_000); // USD → USDC base units

            $settle_body = [
                'payment'             => $payment_data,
                'paymentRequirements' => [
                    'scheme'             => 'exact',
                    'network'            => 'base-mainnet',
                    'maxAmountRequired'  => '0x' . dechex($amount_usdc),
                    'resource'           => home_url('/wc-api/claw_pay?order_id=' . $order_id),
                    'description'        => 'WooCommerce order #' . $order_id,
                    'mimeType'           => 'application/json',
                    'payTo'              => $this->seller_addr,
                    'maxTimeoutSeconds'  => 300,
                    'asset'              => '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
                    'extra'              => ['name' => 'USD Coin', 'version' => '2'],
                ],
                'sellerAddress' => $this->seller_addr,
            ];

            $response = wp_remote_post($this->facilitator . '/settle', [
                'headers' => ['Content-Type' => 'application/json'],
                'body'    => json_encode($settle_body),
                'timeout' => 30,
            ]);

            if (is_wp_error($response)) {
                wp_send_json(['error' => 'Facilitator unreachable'], 502);
            }

            $result = json_decode(wp_remote_retrieve_body($response), true);

            if (!($result['success'] ?? false)) {
                wp_send_json(['error' => 'Payment settlement failed', 'detail' => $result], 402);
            }

            // Mark order as paid
            $order->payment_complete($result['txHash'] ?? '');
            $order->add_order_note('Paid via claw-pay (x402). TxHash: ' . ($result['txHash'] ?? 'n/a'));

            wp_send_json([
                'success' => true,
                'txHash'  => $result['txHash'] ?? '',
                'order'   => $order_id,
                'paid'    => '$' . number_format($order->get_total(), 2) . ' USDC',
            ], 200);
        }

        /**
         * Send HTTP 402 Payment Required with x402 requirements.
         */
        private function send_payment_required(WC_Order $order) {
            $amount_usdc = (int) round($order->get_total() * 1_000_000);
            $resource    = home_url('/wc-api/claw_pay?order_id=' . $order->get_id());

            $payload = [
                'x402Version' => 1,
                'accepts'     => [[
                    'scheme'            => 'exact',
                    'network'           => 'base-mainnet',
                    'maxAmountRequired' => '0x' . dechex($amount_usdc),
                    'resource'          => $resource,
                    'description'       => 'WooCommerce order #' . $order->get_id() . ' — ' . get_bloginfo('name'),
                    'mimeType'          => 'application/json',
                    'payTo'             => $this->seller_addr,
                    'maxTimeoutSeconds' => 300,
                    'asset'             => '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
                    'extra'             => ['name' => 'USD Coin', 'version' => '2'],
                ]],
                'error' => 'X402PaymentRequired',
            ];

            http_response_code(402);
            header('Content-Type: application/json');
            header('PAYMENT-REQUIRED: ' . base64_encode(json_encode($payload)));
            echo json_encode($payload);
            exit;
        }

        /**
         * Standard WooCommerce checkout — not used by agents.
         * Human customers see this gateway as unavailable.
         */
        public function process_payment($order_id) {
            return [
                'result'   => 'success',
                'redirect' => home_url('/wc-api/claw_pay?order_id=' . $order_id),
            ];
        }
    }

    add_filter('woocommerce_payment_gateways', function($gateways) {
        $gateways[] = 'WC_Claw_Pay_Gateway';
        return $gateways;
    });
}
