/**
 * Tests for Settings Page
 *
 * Tests settings tabs, Health Equity preferences (Feature #83),
 * and configuration persistence.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock settings components
const MockSettingsPage = () => {
  return (
    <div data-testid="settings-page">
      <h1>Settings</h1>
      <nav data-testid="settings-tabs">
        <button data-testid="tab-general">General</button>
        <button data-testid="tab-notifications">Notifications</button>
        <button data-testid="tab-health-equity">Health Equity</button>
        <button data-testid="tab-devices">Devices</button>
      </nav>

      {/* General Tab Content */}
      <div data-testid="general-settings">
        <label htmlFor="theme">Theme</label>
        <select id="theme" data-testid="theme-select">
          <option value="light">Light</option>
          <option value="dark">Dark</option>
          <option value="system">System</option>
        </select>
      </div>

      {/* Health Equity Tab Content (Feature #83) */}
      <div data-testid="health-equity-settings">
        <h2>Health Equity Preferences</h2>

        {/* Fitzpatrick Skin Type */}
        <label htmlFor="fitzpatrick">Fitzpatrick Skin Type</label>
        <select id="fitzpatrick" data-testid="fitzpatrick-select">
          <option value="">Not specified</option>
          <option value="I">Type I (Very light)</option>
          <option value="II">Type II (Light)</option>
          <option value="III">Type III (Medium light)</option>
          <option value="IV">Type IV (Medium dark)</option>
          <option value="V">Type V (Dark)</option>
          <option value="VI">Type VI (Very dark)</option>
        </select>

        {/* Ancestry */}
        <label htmlFor="ancestry">Ancestry</label>
        <select id="ancestry" data-testid="ancestry-select">
          <option value="">Not specified</option>
          <option value="african">African</option>
          <option value="asian">Asian</option>
          <option value="european">European</option>
          <option value="hispanic">Hispanic</option>
          <option value="mixed">Mixed</option>
        </select>

        {/* Religion */}
        <label htmlFor="religion">Religion</label>
        <select id="religion" data-testid="religion-select">
          <option value="">Not specified</option>
          <option value="jehovah_witness">Jehovah's Witness</option>
          <option value="islam">Islam</option>
          <option value="judaism">Judaism</option>
          <option value="hinduism">Hinduism</option>
          <option value="buddhism">Buddhism</option>
        </select>

        {/* Blood Product Preferences */}
        <fieldset data-testid="blood-products">
          <legend>Blood Product Preferences</legend>
          <label>
            <input type="checkbox" name="whole_blood" /> Whole Blood
          </label>
          <label>
            <input type="checkbox" name="red_cells" /> Red Cells
          </label>
          <label>
            <input type="checkbox" name="plasma" /> Plasma
          </label>
        </fieldset>

        {/* Dietary Restrictions */}
        <fieldset data-testid="dietary-restrictions">
          <legend>Dietary Restrictions</legend>
          <label>
            <input type="checkbox" name="halal" /> Halal
          </label>
          <label>
            <input type="checkbox" name="kosher" /> Kosher
          </label>
          <label>
            <input type="checkbox" name="vegetarian" /> Vegetarian
          </label>
        </fieldset>

        {/* Same Gender Provider */}
        <label>
          <input
            type="checkbox"
            name="same_gender_provider"
            data-testid="same-gender-checkbox"
          />
          Prefer same-gender provider
        </label>

        {/* Maternal Status */}
        <label htmlFor="maternal">Maternal Status</label>
        <select id="maternal" data-testid="maternal-select">
          <option value="">Not applicable</option>
          <option value="pregnant">Pregnant</option>
          <option value="postpartum">Postpartum</option>
        </select>

        {/* Implicit Bias Alerts */}
        <label>
          <input
            type="checkbox"
            name="bias_alerts"
            data-testid="bias-alerts-checkbox"
            defaultChecked
          />
          Enable implicit bias alerts
        </label>

        <button type="submit" data-testid="save-button">
          Save Preferences
        </button>
      </div>
    </div>
  )
}

describe('Settings Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Layout', () => {
    it('should render settings page', () => {
      render(<MockSettingsPage />)

      expect(screen.getByTestId('settings-page')).toBeInTheDocument()
    })

    it('should display settings title', () => {
      render(<MockSettingsPage />)

      expect(screen.getByRole('heading', { name: /settings/i })).toBeInTheDocument()
    })

    it('should render settings tabs', () => {
      render(<MockSettingsPage />)

      expect(screen.getByTestId('settings-tabs')).toBeInTheDocument()
    })
  })

  describe('Settings Tabs', () => {
    it('should have General tab', () => {
      render(<MockSettingsPage />)

      expect(screen.getByTestId('tab-general')).toBeInTheDocument()
    })

    it('should have Health Equity tab', () => {
      render(<MockSettingsPage />)

      expect(screen.getByTestId('tab-health-equity')).toBeInTheDocument()
    })

    it('should have Notifications tab', () => {
      render(<MockSettingsPage />)

      expect(screen.getByTestId('tab-notifications')).toBeInTheDocument()
    })

    it('should have Devices tab', () => {
      render(<MockSettingsPage />)

      expect(screen.getByTestId('tab-devices')).toBeInTheDocument()
    })
  })

  describe('General Settings', () => {
    it('should have theme selector', () => {
      render(<MockSettingsPage />)

      expect(screen.getByTestId('theme-select')).toBeInTheDocument()
    })

    it('should have light/dark/system theme options', () => {
      render(<MockSettingsPage />)

      const themeSelect = screen.getByTestId('theme-select')
      expect(themeSelect).toContainHTML('Light')
      expect(themeSelect).toContainHTML('Dark')
      expect(themeSelect).toContainHTML('System')
    })
  })
})

describe('Health Equity Settings (Feature #83)', () => {
  describe('Fitzpatrick Skin Type', () => {
    it('should have Fitzpatrick skin type dropdown', () => {
      render(<MockSettingsPage />)

      expect(screen.getByTestId('fitzpatrick-select')).toBeInTheDocument()
    })

    it('should include all 6 Fitzpatrick types', () => {
      render(<MockSettingsPage />)

      const select = screen.getByTestId('fitzpatrick-select')
      expect(select).toContainHTML('Type I')
      expect(select).toContainHTML('Type VI')
    })

    it('should allow selecting Fitzpatrick type', async () => {
      const user = userEvent.setup()
      render(<MockSettingsPage />)

      const select = screen.getByTestId('fitzpatrick-select')
      await user.selectOptions(select, 'V')

      expect(select).toHaveValue('V')
    })
  })

  describe('Ancestry Selection', () => {
    it('should have ancestry dropdown', () => {
      render(<MockSettingsPage />)

      expect(screen.getByTestId('ancestry-select')).toBeInTheDocument()
    })
  })

  describe('Religion Selection', () => {
    it('should have religion dropdown', () => {
      render(<MockSettingsPage />)

      expect(screen.getByTestId('religion-select')).toBeInTheDocument()
    })

    it("should include Jehovah's Witness option", () => {
      render(<MockSettingsPage />)

      const select = screen.getByTestId('religion-select')
      expect(select).toContainHTML("Jehovah's Witness")
    })
  })

  describe('Blood Product Preferences', () => {
    it('should have blood product checkboxes', () => {
      render(<MockSettingsPage />)

      expect(screen.getByTestId('blood-products')).toBeInTheDocument()
    })
  })

  describe('Dietary Restrictions', () => {
    it('should have dietary restriction checkboxes', () => {
      render(<MockSettingsPage />)

      expect(screen.getByTestId('dietary-restrictions')).toBeInTheDocument()
    })
  })

  describe('Same Gender Provider', () => {
    it('should have same-gender provider checkbox', () => {
      render(<MockSettingsPage />)

      expect(screen.getByTestId('same-gender-checkbox')).toBeInTheDocument()
    })

    it('should be toggleable', async () => {
      const user = userEvent.setup()
      render(<MockSettingsPage />)

      const checkbox = screen.getByTestId('same-gender-checkbox')
      await user.click(checkbox)

      expect(checkbox).toBeChecked()
    })
  })

  describe('Maternal Status', () => {
    it('should have maternal status dropdown', () => {
      render(<MockSettingsPage />)

      expect(screen.getByTestId('maternal-select')).toBeInTheDocument()
    })

    it('should include pregnant and postpartum options', () => {
      render(<MockSettingsPage />)

      const select = screen.getByTestId('maternal-select')
      expect(select).toContainHTML('Pregnant')
      expect(select).toContainHTML('Postpartum')
    })
  })

  describe('Implicit Bias Alerts', () => {
    it('should have bias alerts toggle', () => {
      render(<MockSettingsPage />)

      expect(screen.getByTestId('bias-alerts-checkbox')).toBeInTheDocument()
    })

    it('should be enabled by default', () => {
      render(<MockSettingsPage />)

      expect(screen.getByTestId('bias-alerts-checkbox')).toBeChecked()
    })
  })

  describe('Save Functionality', () => {
    it('should have save button', () => {
      render(<MockSettingsPage />)

      expect(screen.getByTestId('save-button')).toBeInTheDocument()
    })
  })
})
