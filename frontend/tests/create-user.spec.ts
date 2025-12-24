import { test, expect } from '@playwright/test';

// Test credentials
const TEST_EMAIL = process.env.TEST_EMAIL || 'admin@example.com';
const TEST_PASSWORD = process.env.TEST_PASSWORD || 'admin123';

// New user to create
const NEW_USER_EMAIL = 'aldanesmith@gmail.com';
const NEW_USER_PASSWORD = 'admin';
const NEW_USER_FIRST = 'Aldane';
const NEW_USER_LAST = 'Smith';

test('Create new admin user', async ({ page }) => {
  // Login first
  await page.goto('/login');
  await page.waitForLoadState('networkidle');

  const emailInput = page.locator('input[type="email"]');
  await emailInput.waitFor({ state: 'visible', timeout: 30000 });
  await emailInput.fill(TEST_EMAIL);
  await page.locator('input[type="password"]').fill(TEST_PASSWORD);
  await page.locator('button[type="submit"]').click();

  await page.waitForLoadState('networkidle');
  await expect(page.locator('text=Welcome back')).toBeVisible({ timeout: 30000 });
  console.log('Logged in successfully');

  // Navigate to Settings
  await page.locator('a:has-text("Settings")').click();
  await page.waitForLoadState('networkidle');
  console.log('Navigated to Settings');

  // Click Users tab
  const usersTab = page.locator('button:has-text("Users")');
  await usersTab.click();
  await page.waitForTimeout(3000);
  console.log('Clicked Users tab');

  // Wait for User Management to load
  await expect(page.locator('text=User Management')).toBeVisible({ timeout: 15000 });
  console.log('User Management loaded');

  // Click Add User button
  const addUserBtn = page.locator('button:has-text("Add User")');
  await expect(addUserBtn).toBeVisible({ timeout: 10000 });
  await addUserBtn.click();
  console.log('Clicked Add User button');

  // Wait for the dialog to appear
  await expect(page.locator('text=Add New User')).toBeVisible({ timeout: 10000 });
  console.log('Dialog opened');

  // Fill in first name
  await page.locator('#first_name').fill(NEW_USER_FIRST);
  console.log('Filled first name');

  // Fill in last name
  await page.locator('#last_name').fill(NEW_USER_LAST);
  console.log('Filled last name');

  // Fill in email
  await page.locator('#email').fill(NEW_USER_EMAIL);
  console.log('Filled email');

  // Fill in password
  await page.locator('#password').fill(NEW_USER_PASSWORD);
  console.log('Filled password');

  // Select Admin role - using keyboard navigation for Radix Select
  const roleDropdown = page.locator('[role="combobox"]:has-text("Operator")');
  await roleDropdown.click();
  await page.waitForTimeout(500);

  // Wait for dropdown to open and select Administrator using role locator
  const adminOption = page.getByRole('option', { name: /Administrator/i }).first();
  await adminOption.waitFor({ state: 'visible', timeout: 5000 });
  await adminOption.click();
  console.log('Selected Administrator role');

  // Take screenshot before submitting
  await page.screenshot({ path: 'create-user-form.png' });

  // Submit the form by clicking "Create User" button
  await page.locator('button:has-text("Create User")').click();
  console.log('Submitted form');

  // Wait for response and dialog to close
  await page.waitForTimeout(3000);

  // Check if dialog closed (success) or error appeared
  const dialogVisible = await page.locator('text=Add New User').isVisible();

  if (!dialogVisible) {
    console.log('User created successfully - dialog closed!');

    // Verify user appears in the list
    const userInList = await page.locator(`text=${NEW_USER_EMAIL}`).count();
    if (userInList > 0) {
      console.log('New user appears in the user list!');
    }
  } else {
    // Check for error message
    const errorMsg = await page.locator('.bg-destructive\\/10').textContent();
    console.log('Error creating user:', errorMsg);
  }

  // Take final screenshot
  await page.screenshot({ path: 'create-user-result.png' });
});
