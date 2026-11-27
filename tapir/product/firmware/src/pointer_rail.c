// The PS/2 driver initializes at 40, and its mouse device at 90. ZMK system-off
// wakes through a full reset on nRF52. No persistent power-toggle state.
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/pm/device.h>
#include <zephyr/sys/reboot.h>

#define RAIL DT_NODELABEL(tp_rail)
static const struct gpio_dt_spec en = GPIO_DT_SPEC_GET(RAIL, enable_gpios);
static const struct gpio_dt_spec clk = GPIO_DT_SPEC_GET(DT_NODELABEL(ps2bus), scl_gpios);
static const struct gpio_dt_spec dat = GPIO_DT_SPEC_GET(DT_NODELABEL(ps2bus), sda_gpios);
static const struct gpio_dt_spec rst = GPIO_DT_SPEC_GET(DT_NODELABEL(stick), rst_gpios);

static int power_init(const struct device *dev) {
    ARG_UNUSED(dev);
    if (!gpio_is_ready_dt(&en) || !gpio_is_ready_dt(&rst) ||
        !gpio_is_ready_dt(&clk) || !gpio_is_ready_dt(&dat)) return -ENODEV;
    int rc = gpio_pin_configure_dt(&rst, GPIO_OUTPUT_INACTIVE);
    if (rc) return rc;
    return gpio_pin_configure_dt(&en, GPIO_OUTPUT_ACTIVE);
}

static int power_action(const struct device *dev, enum pm_device_action action) {
    ARG_UNUSED(dev);
    switch (action) {
    case PM_DEVICE_ACTION_SUSPEND: {
        // Only system-off, not normal idle: the rail stays on while we can point.
        // First remove sources of back-power; externally pulled-up PS/2 lines
        // discharge with TP_3V3. No internal pullups or push-pull highs.
        int rc = gpio_pin_interrupt_configure_dt(&clk, GPIO_INT_DISABLE);
        if (!rc) rc = gpio_pin_configure_dt(&dat, GPIO_DISCONNECTED);
        if (!rc) rc = gpio_pin_configure_dt(&clk, GPIO_DISCONNECTED);
        if (!rc) rc = gpio_pin_configure_dt(&rst, GPIO_OUTPUT_INACTIVE);
        if (!rc) rc = gpio_pin_set_dt(&en, 0);
        if (rc) sys_reboot(SYS_REBOOT_COLD); // cannot safely leave a half-suspended bus
        return rc;
    }
    case PM_DEVICE_ACTION_RESUME:
        // Reached only if ZMK's device suspend pass is aborted, not on normal
        // nRF52 wake. Never repower the sensor without repeating the handshake.
        sys_reboot(SYS_REBOOT_COLD);
        return 0;
    default:
        return -ENOTSUP;
    }
}
PM_DEVICE_DT_DEFINE(RAIL, power_action);
DEVICE_DT_DEFINE(RAIL, power_init, PM_DEVICE_DT_GET(RAIL), NULL, NULL, POST_KERNEL, 85, NULL);
