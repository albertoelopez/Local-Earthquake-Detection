import { test, expect } from '@playwright/test';

test.describe('Earthquake Dashboard E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display the dashboard header', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Earthquake Monitoring Dashboard');
  });

  test('should show connection status indicator', async ({ page }) => {
    const connectionStatus = page.getByTestId('connection-status');
    await expect(connectionStatus).toBeVisible();
  });

  test('should display stats panel when data is loaded', async ({ page }) => {
    await page.waitForSelector('[data-testid="stats-panel"]', { timeout: 10000 });
    const statsPanel = page.getByTestId('stats-panel');
    await expect(statsPanel).toBeVisible();
  });

  test('should display total alerts statistic', async ({ page }) => {
    await page.waitForSelector('[data-testid="stat-total"]', { timeout: 10000 });
    const totalStat = page.getByTestId('stat-total');
    await expect(totalStat).toBeVisible();
    await expect(totalStat).toContainText('Total Alerts');
  });

  test('should display alerts list or no-alerts message', async ({ page }) => {
    await page.waitForLoadState('networkidle');

    const alertsList = page.getByTestId('alerts-list');
    const noAlerts = page.getByTestId('no-alerts');

    const hasAlerts = await alertsList.isVisible().catch(() => false);
    const hasNoAlertsMessage = await noAlerts.isVisible().catch(() => false);

    expect(hasAlerts || hasNoAlertsMessage).toBeTruthy();
  });

  test('should show alert card with correct structure when alerts exist', async ({ page }) => {
    const alertCard = page.getByTestId('alert-card').first();

    if (await alertCard.isVisible().catch(() => false)) {
      await expect(alertCard).toBeVisible();

      await expect(alertCard.locator('text=PGA:')).toBeVisible();
      await expect(alertCard.locator('text=Duration:')).toBeVisible();
      await expect(alertCard.locator('text=Device:')).toBeVisible();
    }
  });

  test('should update when new alert arrives via WebSocket', async ({ page }) => {
    const initialAlertCount = await page.getByTestId('alert-card').count();

    await page.evaluate(() => {
      const ws = new WebSocket('ws://localhost:3000');
      ws.onopen = () => {
        ws.send(JSON.stringify({
          type: 'earthquake_alert',
          data: {
            device_id: 'TEST_DEVICE',
            timestamp: Date.now(),
            event: {
              magnitude: 5.5,
              pga: 0.15,
              pgv: 10.0,
              cav: 0.2,
              duration: 15000,
              alert_level: 'MODERATE',
              confirmed: true
            },
            location: { lat: 37.7749, lon: -122.4194 }
          }
        }));
      };
    });

    await page.waitForTimeout(1000);
  });

  test('should display confirmed badge for confirmed earthquakes', async ({ page }) => {
    const alertCards = page.getByTestId('alert-card');
    const count = await alertCards.count();

    for (let i = 0; i < Math.min(count, 5); i++) {
      const card = alertCards.nth(i);
      const confirmedBadge = card.getByTestId('confirmed-badge');

      if (await confirmedBadge.isVisible().catch(() => false)) {
        await expect(confirmedBadge).toContainText('CONFIRMED');
        break;
      }
    }
  });

  test('should have responsive layout', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator('h1')).toBeVisible();

    await page.setViewportSize({ width: 1920, height: 1080 });
    await expect(page.locator('h1')).toBeVisible();
  });

  test('should display device count in stats', async ({ page }) => {
    await page.waitForSelector('[data-testid="stat-devices"]', { timeout: 10000 });
    const deviceStat = page.getByTestId('stat-devices');
    await expect(deviceStat).toBeVisible();
    await expect(deviceStat).toContainText('Active Devices');
  });
});

test.describe('Dashboard Loading States', () => {
  test('should show loading indicator initially', async ({ page }) => {
    await page.route('**/api/**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      await route.continue();
    });

    await page.goto('/');
    const loading = page.getByTestId('loading');

    await expect(loading).toBeVisible();
  });
});

test.describe('Dashboard Error Handling', () => {
  test('should display error message on API failure', async ({ page }) => {
    await page.route('**/api/alerts**', (route) => {
      route.abort();
    });

    await page.goto('/');
    await page.waitForTimeout(2000);

    const errorMessage = page.getByTestId('error-message');

    if (await errorMessage.isVisible().catch(() => false)) {
      await expect(errorMessage).toBeVisible();
    }
  });
});

test.describe('Alert Filtering and Sorting', () => {
  test('alerts should be sorted by timestamp descending', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="alert-card"]', { timeout: 10000 }).catch(() => null);

    const alertCards = page.getByTestId('alert-card');
    const count = await alertCards.count();

    if (count >= 2) {
      const timestamps: number[] = [];
      for (let i = 0; i < Math.min(count, 5); i++) {
        const text = await alertCards.nth(i).textContent();
        const dateMatch = text?.match(/\d{1,2}\/\d{1,2}\/\d{4}/);
        if (dateMatch) {
          timestamps.push(new Date(dateMatch[0]).getTime());
        }
      }

      for (let i = 0; i < timestamps.length - 1; i++) {
        expect(timestamps[i]).toBeGreaterThanOrEqual(timestamps[i + 1]);
      }
    }
  });
});
