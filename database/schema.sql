CREATE DATABASE ecompro
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE ecompro;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('ADMIN', 'VENDOR', 'CUSTOMER', 'DELIVERY_PARTNER') NOT NULL DEFAULT 'CUSTOMER',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_users_username (username),
    INDEX idx_users_email (email)
) ENGINE = InnoDB;

CREATE TABLE addresses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    address_line VARCHAR(255) NOT NULL,
    city VARCHAR(80) NOT NULL,
    state VARCHAR(80) NOT NULL,
    pincode VARCHAR(20) NOT NULL,
    INDEX idx_addresses_user_id (user_id),
    CONSTRAINT fk_addresses_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE = InnoDB;

CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE
) ENGINE = InnoDB;

CREATE TABLE brands (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE
) ENGINE = InnoDB;

CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT NOT NULL,
    brand_id INT NULL,
    vendor_id INT NOT NULL,
    name VARCHAR(180) NOT NULL,
    description TEXT NULL,
    price DECIMAL(12, 2) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_products_category_id (category_id),
    INDEX idx_products_brand_id (brand_id),
    INDEX idx_products_vendor_id (vendor_id),
    INDEX idx_products_name (name),
    CONSTRAINT fk_products_category
        FOREIGN KEY (category_id) REFERENCES categories(id),
    CONSTRAINT fk_products_brand
        FOREIGN KEY (brand_id) REFERENCES brands(id),
    CONSTRAINT fk_products_vendor
        FOREIGN KEY (vendor_id) REFERENCES users(id),
    CONSTRAINT ck_products_price_positive CHECK (price > 0)
) ENGINE = InnoDB;

CREATE TABLE product_images (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    image_url VARCHAR(500) NOT NULL,
    INDEX idx_product_images_product_id (product_id),
    CONSTRAINT fk_product_images_product
        FOREIGN KEY (product_id) REFERENCES products(id)
        ON DELETE CASCADE
) ENGINE = InnoDB;

CREATE TABLE inventory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL UNIQUE,
    stock_quantity INT NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_inventory_product_id (product_id),
    CONSTRAINT fk_inventory_product
        FOREIGN KEY (product_id) REFERENCES products(id)
        ON DELETE CASCADE,
    CONSTRAINT ck_inventory_stock_non_negative CHECK (stock_quantity >= 0)
) ENGINE = InnoDB;

CREATE TABLE coupons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    coupon_code VARCHAR(40) NOT NULL UNIQUE,
    discount_percentage DECIMAL(5, 2) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    INDEX idx_coupons_coupon_code (coupon_code),
    CONSTRAINT ck_coupons_discount_range CHECK (discount_percentage >= 0 AND discount_percentage <= 100)
) ENGINE = InnoDB;

CREATE TABLE carts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL UNIQUE,
    coupon_id INT NULL,
    INDEX idx_carts_customer_id (customer_id),
    CONSTRAINT fk_carts_customer
        FOREIGN KEY (customer_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_carts_coupon
        FOREIGN KEY (coupon_id) REFERENCES coupons(id)
) ENGINE = InnoDB;

CREATE TABLE cart_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cart_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    UNIQUE KEY uq_cart_product (cart_id, product_id),
    INDEX idx_cart_items_cart_id (cart_id),
    INDEX idx_cart_items_product_id (product_id),
    CONSTRAINT fk_cart_items_cart
        FOREIGN KEY (cart_id) REFERENCES carts(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_cart_items_product
        FOREIGN KEY (product_id) REFERENCES products(id),
    CONSTRAINT ck_cart_items_quantity_positive CHECK (quantity > 0)
) ENGINE = InnoDB;

CREATE TABLE wishlists (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL UNIQUE,
    INDEX idx_wishlists_customer_id (customer_id),
    CONSTRAINT fk_wishlists_customer
        FOREIGN KEY (customer_id) REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE = InnoDB;

CREATE TABLE wishlist_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    wishlist_id INT NOT NULL,
    product_id INT NOT NULL,
    UNIQUE KEY uq_wishlist_product (wishlist_id, product_id),
    INDEX idx_wishlist_items_wishlist_id (wishlist_id),
    INDEX idx_wishlist_items_product_id (product_id),
    CONSTRAINT fk_wishlist_items_wishlist
        FOREIGN KEY (wishlist_id) REFERENCES wishlists(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_wishlist_items_product
        FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE = InnoDB;

CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    total_amount DECIMAL(12, 2) NOT NULL,
    status ENUM(
        'PENDING_PAYMENT',
        'PAID',
        'PROCESSING',
        'SHIPPED',
        'DELIVERED',
        'CANCELLED',
        'RETURN_REQUESTED',
        'RETURN_APPROVED',
        'RETURNED'
    ) NOT NULL DEFAULT 'PENDING_PAYMENT',
    coupon_id INT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    paid_at DATETIME NULL,
    INDEX idx_orders_customer_id (customer_id),
    INDEX idx_orders_status (status),
    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id) REFERENCES users(id),
    CONSTRAINT fk_orders_coupon
        FOREIGN KEY (coupon_id) REFERENCES coupons(id),
    CONSTRAINT ck_orders_total_non_negative CHECK (total_amount >= 0)
) ENGINE = InnoDB;

CREATE TABLE order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(12, 2) NOT NULL,
    INDEX idx_order_items_order_id (order_id),
    INDEX idx_order_items_product_id (product_id),
    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id) REFERENCES orders(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_id) REFERENCES products(id),
    CONSTRAINT ck_order_items_quantity_positive CHECK (quantity > 0),
    CONSTRAINT ck_order_items_price_positive CHECK (price > 0)
) ENGINE = InnoDB;

CREATE TABLE shipping_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL UNIQUE,
    address_id INT NOT NULL,
    delivery_partner_id INT NULL,
    delivery_status ENUM('ASSIGNED', 'PICKED_UP', 'IN_TRANSIT', 'DELIVERED', 'FAILED') NOT NULL DEFAULT 'ASSIGNED',
    INDEX idx_shipping_order_id (order_id),
    INDEX idx_shipping_delivery_partner_id (delivery_partner_id),
    CONSTRAINT fk_shipping_order
        FOREIGN KEY (order_id) REFERENCES orders(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_shipping_address
        FOREIGN KEY (address_id) REFERENCES addresses(id),
    CONSTRAINT fk_shipping_delivery_partner
        FOREIGN KEY (delivery_partner_id) REFERENCES users(id)
) ENGINE = InnoDB;

CREATE TABLE payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL UNIQUE,
    amount DECIMAL(12, 2) NOT NULL,
    payment_method ENUM('CARD', 'UPI', 'NET_BANKING', 'CASH_ON_DELIVERY') NOT NULL,
    payment_status ENUM('PENDING', 'SUCCESS', 'FAILED', 'REFUNDED') NOT NULL DEFAULT 'PENDING',
    transaction_reference VARCHAR(120) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_payments_order_id (order_id),
    CONSTRAINT fk_payments_order
        FOREIGN KEY (order_id) REFERENCES orders(id),
    CONSTRAINT ck_payments_amount_positive CHECK (amount > 0)
) ENGINE = InnoDB;

CREATE TABLE refunds (
    id INT AUTO_INCREMENT PRIMARY KEY,
    payment_id INT NOT NULL,
    refund_amount DECIMAL(12, 2) NOT NULL,
    refund_status ENUM('PENDING', 'APPROVED', 'REJECTED', 'PROCESSED') NOT NULL DEFAULT 'PENDING',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_refunds_payment_id (payment_id),
    CONSTRAINT fk_refunds_payment
        FOREIGN KEY (payment_id) REFERENCES payments(id),
    CONSTRAINT ck_refunds_amount_positive CHECK (refund_amount > 0)
) ENGINE = InnoDB;

CREATE TABLE reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    customer_id INT NOT NULL,
    rating INT NOT NULL,
    review_text TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_product_customer_review (product_id, customer_id),
    INDEX idx_reviews_product_id (product_id),
    INDEX idx_reviews_customer_id (customer_id),
    CONSTRAINT fk_reviews_product
        FOREIGN KEY (product_id) REFERENCES products(id),
    CONSTRAINT fk_reviews_customer
        FOREIGN KEY (customer_id) REFERENCES users(id),
    CONSTRAINT ck_reviews_rating CHECK (rating >= 1 AND rating <= 5)
) ENGINE = InnoDB;

CREATE TABLE coupon_usage (
    id INT AUTO_INCREMENT PRIMARY KEY,
    coupon_id INT NOT NULL,
    customer_id INT NOT NULL,
    used_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_coupon_customer (coupon_id, customer_id),
    INDEX idx_coupon_usage_coupon_id (coupon_id),
    INDEX idx_coupon_usage_customer_id (customer_id),
    CONSTRAINT fk_coupon_usage_coupon
        FOREIGN KEY (coupon_id) REFERENCES coupons(id),
    CONSTRAINT fk_coupon_usage_customer
        FOREIGN KEY (customer_id) REFERENCES users(id)
) ENGINE = InnoDB;

CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(120) NOT NULL,
    message VARCHAR(500) NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_notifications_user_id (user_id),
    CONSTRAINT fk_notifications_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE = InnoDB;

CREATE TABLE audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(120) NOT NULL,
    entity VARCHAR(120) NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_logs_user_id (user_id),
    CONSTRAINT fk_audit_logs_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE SET NULL
) ENGINE = InnoDB;

CREATE TABLE return_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    customer_id INT NOT NULL,
    reason VARCHAR(500) NOT NULL,
    status ENUM('REQUESTED', 'APPROVED', 'REJECTED', 'REFUNDED') NOT NULL DEFAULT 'REQUESTED',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_return_requests_order_id (order_id),
    INDEX idx_return_requests_customer_id (customer_id),
    CONSTRAINT fk_return_requests_order
        FOREIGN KEY (order_id) REFERENCES orders(id),
    CONSTRAINT fk_return_requests_customer
        FOREIGN KEY (customer_id) REFERENCES users(id)
) ENGINE = InnoDB;

CREATE TABLE invoices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL UNIQUE,
    invoice_number VARCHAR(80) NOT NULL UNIQUE,
    subtotal DECIMAL(12, 2) NOT NULL,
    tax_amount DECIMAL(12, 2) NOT NULL,
    discount_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    total_amount DECIMAL(12, 2) NOT NULL,
    generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_invoices_order_id (order_id),
    CONSTRAINT fk_invoices_order
        FOREIGN KEY (order_id) REFERENCES orders(id)
        ON DELETE CASCADE,
    CONSTRAINT ck_invoices_amounts_non_negative CHECK (
        subtotal >= 0
        AND tax_amount >= 0
        AND discount_amount >= 0
        AND total_amount >= 0
    )
) ENGINE = InnoDB;
