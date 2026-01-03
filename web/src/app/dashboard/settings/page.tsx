'use client';

import { useState } from 'react';
import { Save, User, Bell, Shield, Database, Mic, Heart, AlertTriangle, Baby } from 'lucide-react';

// Equity settings types
interface EquitySettings {
  skinType: string;
  ancestry: string;
  religion: string;
  dietaryRestrictions: string[];
  bloodProductPreferences: {
    wholeBood: boolean;
    redCells: boolean;
    plasma: boolean;
    platelets: boolean;
    albumin: boolean;
    immunoglobulins: boolean;
    cellSalvage: boolean;
  };
  sameGenderProvider: boolean;
  decisionMakingStyle: string;
  maternalStatus: string;
  biasAlertsEnabled: boolean;
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('profile');
  const [equitySettings, setEquitySettings] = useState<EquitySettings>({
    skinType: '',
    ancestry: '',
    religion: '',
    dietaryRestrictions: [],
    bloodProductPreferences: {
      wholeBood: true,
      redCells: true,
      plasma: true,
      platelets: true,
      albumin: true,
      immunoglobulins: true,
      cellSalvage: true,
    },
    sameGenderProvider: false,
    decisionMakingStyle: 'individual',
    maternalStatus: '',
    biasAlertsEnabled: true,
  });
  const [equitySaved, setEquitySaved] = useState(false);

  const tabs = [
    { id: 'profile', name: 'Profile', icon: User },
    { id: 'notifications', name: 'Notifications', icon: Bell },
    { id: 'security', name: 'Security', icon: Shield },
    { id: 'integrations', name: 'EHR Integrations', icon: Database },
    { id: 'transcription', name: 'Transcription', icon: Mic },
    { id: 'equity', name: 'Health Equity', icon: Heart },
  ];

  const fitzpatrickTypes = [
    { value: 'I', label: 'Type I - Very light, always burns, never tans' },
    { value: 'II', label: 'Type II - Light, burns easily, tans minimally' },
    { value: 'III', label: 'Type III - Medium, burns moderately, tans gradually' },
    { value: 'IV', label: 'Type IV - Olive, burns minimally, tans well' },
    { value: 'V', label: 'Type V - Brown, rarely burns, tans darkly' },
    { value: 'VI', label: 'Type VI - Dark brown/black, never burns' },
  ];

  const ancestryOptions = [
    { value: '', label: 'Not specified' },
    { value: 'african', label: 'African / Black' },
    { value: 'east_asian', label: 'East Asian' },
    { value: 'south_asian', label: 'South Asian' },
    { value: 'european', label: 'European / Caucasian' },
    { value: 'hispanic', label: 'Hispanic / Latino' },
    { value: 'middle_eastern', label: 'Middle Eastern' },
    { value: 'native_american', label: 'Native American / Indigenous' },
    { value: 'pacific_islander', label: 'Pacific Islander' },
    { value: 'mixed', label: 'Mixed / Multiple' },
  ];

  const religionOptions = [
    { value: '', label: 'Not specified' },
    { value: 'jehovah_witness', label: "Jehovah's Witness" },
    { value: 'islam', label: 'Islam / Muslim' },
    { value: 'judaism', label: 'Judaism / Jewish' },
    { value: 'hinduism', label: 'Hinduism / Hindu' },
    { value: 'buddhism', label: 'Buddhism / Buddhist' },
    { value: 'sikhism', label: 'Sikhism / Sikh' },
    { value: 'catholic', label: 'Catholic' },
    { value: 'christian', label: 'Christian (Other)' },
    { value: 'other', label: 'Other' },
  ];

  const dietaryOptions = [
    'Halal',
    'Kosher',
    'Vegetarian',
    'Vegan',
    'No pork',
    'No beef',
    'No gelatin',
    'No alcohol in medications',
    'Gluten-free (medical)',
    'Lactose-free',
  ];

  const handleDietaryChange = (option: string) => {
    setEquitySettings(prev => ({
      ...prev,
      dietaryRestrictions: prev.dietaryRestrictions.includes(option)
        ? prev.dietaryRestrictions.filter(d => d !== option)
        : [...prev.dietaryRestrictions, option]
    }));
  };

  const handleBloodPreferenceChange = (key: keyof typeof equitySettings.bloodProductPreferences) => {
    setEquitySettings(prev => ({
      ...prev,
      bloodProductPreferences: {
        ...prev.bloodProductPreferences,
        [key]: !prev.bloodProductPreferences[key]
      }
    }));
  };

  const saveEquitySettings = () => {
    // In production, this would save to backend
    console.log('Saving equity settings:', equitySettings);
    setEquitySaved(true);
    setTimeout(() => setEquitySaved(false), 3000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Settings
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Manage your account and application preferences
        </p>
      </div>

      <div className="flex gap-6">
        <div className="w-64 flex-shrink-0">
          <nav className="space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={'w-full flex items-center gap-3 px-4 py-2 text-sm font-medium rounded-lg transition-colors ' + (activeTab === tab.id
                  ? 'bg-mdx-primary/10 text-mdx-primary'
                  : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800')}
              >
                <tab.icon className="h-5 w-5" />
                {tab.name}
              </button>
            ))}
          </nav>
        </div>

        <div className="flex-1">
          {activeTab === 'profile' && (
            <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">
                Profile Settings
              </h2>
              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      First Name
                    </label>
                    <input
                      type="text"
                      defaultValue="Rafael"
                      className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-mdx-primary focus:outline-none focus:ring-1 focus:ring-mdx-primary dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Last Name
                    </label>
                    <input
                      type="text"
                      defaultValue="Rodriguez"
                      className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-mdx-primary focus:outline-none focus:ring-1 focus:ring-mdx-primary dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Email
                  </label>
                  <input
                    type="email"
                    defaultValue="rafael@mdxvision.com"
                    className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-mdx-primary focus:outline-none focus:ring-1 focus:ring-mdx-primary dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    NPI Number
                  </label>
                  <input
                    type="text"
                    defaultValue="1234567890"
                    className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-mdx-primary focus:outline-none focus:ring-1 focus:ring-mdx-primary dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Specialty
                  </label>
                  <select className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-mdx-primary focus:outline-none focus:ring-1 focus:ring-mdx-primary dark:border-gray-700 dark:bg-gray-900 dark:text-white">
                    <option>Internal Medicine</option>
                    <option>Family Medicine</option>
                    <option>Emergency Medicine</option>
                    <option>Surgery</option>
                    <option>Pediatrics</option>
                  </select>
                </div>
                <div className="pt-4">
                  <button className="inline-flex items-center gap-2 rounded-lg bg-mdx-primary px-4 py-2 text-sm font-medium text-white hover:bg-mdx-primary/90 transition-colors">
                    <Save className="h-4 w-4" />
                    Save Changes
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'integrations' && (
            <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">
                EHR Integrations
              </h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg dark:border-gray-700">
                  <div className="flex items-center gap-4">
                    <div className="h-12 w-12 rounded-lg bg-red-100 flex items-center justify-center">
                      <span className="text-lg font-bold text-red-600">E</span>
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900 dark:text-white">Epic</h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Connect to Epic MyChart</p>
                    </div>
                  </div>
                  <button className="rounded-lg bg-mdx-primary px-4 py-2 text-sm font-medium text-white hover:bg-mdx-primary/90">
                    Connect
                  </button>
                </div>
                <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg dark:border-gray-700">
                  <div className="flex items-center gap-4">
                    <div className="h-12 w-12 rounded-lg bg-blue-100 flex items-center justify-center">
                      <span className="text-lg font-bold text-blue-600">C</span>
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900 dark:text-white">Cerner</h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Connect to Cerner Millennium</p>
                    </div>
                  </div>
                  <button className="rounded-lg bg-mdx-primary px-4 py-2 text-sm font-medium text-white hover:bg-mdx-primary/90">
                    Connect
                  </button>
                </div>
                <div className="flex items-center justify-between p-4 border border-green-200 rounded-lg bg-green-50 dark:border-green-800 dark:bg-green-900/20">
                  <div className="flex items-center gap-4">
                    <div className="h-12 w-12 rounded-lg bg-green-100 flex items-center justify-center">
                      <span className="text-lg font-bold text-green-600">A</span>
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900 dark:text-white">Athenahealth</h3>
                      <p className="text-sm text-green-600 dark:text-green-400">Connected</p>
                    </div>
                  </div>
                  <button className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50">
                    Disconnect
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'transcription' && (
            <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">
                Transcription Settings
              </h2>
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Default Note Type
                  </label>
                  <select className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-mdx-primary focus:outline-none focus:ring-1 focus:ring-mdx-primary dark:border-gray-700 dark:bg-gray-900 dark:text-white">
                    <option>SOAP Note</option>
                    <option>Progress Note</option>
                    <option>Procedure Note</option>
                    <option>Discharge Summary</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Language
                  </label>
                  <select className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-mdx-primary focus:outline-none focus:ring-1 focus:ring-mdx-primary dark:border-gray-700 dark:bg-gray-900 dark:text-white">
                    <option>English (US)</option>
                    <option>Spanish</option>
                    <option>French</option>
                    <option>German</option>
                  </select>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">Auto-generate ICD codes</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Automatically suggest diagnosis codes</p>
                  </div>
                  <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-mdx-primary">
                    <span className="translate-x-6 inline-block h-4 w-4 transform rounded-full bg-white transition" />
                  </button>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">Auto-generate CPT codes</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Automatically suggest procedure codes</p>
                  </div>
                  <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-mdx-primary">
                    <span className="translate-x-6 inline-block h-4 w-4 transform rounded-full bg-white transition" />
                  </button>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">Drug Interaction Alerts</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Alert when potential interactions detected</p>
                  </div>
                  <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-mdx-primary">
                    <span className="translate-x-6 inline-block h-4 w-4 transform rounded-full bg-white transition" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">
                Notification Preferences
              </h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between py-2">
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">Session Complete</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Notify when transcription is ready</p>
                  </div>
                  <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-mdx-primary">
                    <span className="translate-x-6 inline-block h-4 w-4 transform rounded-full bg-white transition" />
                  </button>
                </div>
                <div className="flex items-center justify-between py-2">
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">Note Pending Review</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Notify when notes need approval</p>
                  </div>
                  <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-mdx-primary">
                    <span className="translate-x-6 inline-block h-4 w-4 transform rounded-full bg-white transition" />
                  </button>
                </div>
                <div className="flex items-center justify-between py-2">
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">Drug Interaction Alerts</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Immediate alerts for interactions</p>
                  </div>
                  <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-mdx-primary">
                    <span className="translate-x-6 inline-block h-4 w-4 transform rounded-full bg-white transition" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">
                Security Settings
              </h2>
              <div className="space-y-6">
                <div>
                  <button className="rounded-lg bg-mdx-primary px-4 py-2 text-sm font-medium text-white hover:bg-mdx-primary/90">
                    Change Password
                  </button>
                </div>
                <div className="flex items-center justify-between py-2">
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">Two-Factor Authentication</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Add an extra layer of security</p>
                  </div>
                  <button className="rounded-lg border border-mdx-primary px-4 py-2 text-sm font-medium text-mdx-primary hover:bg-mdx-primary/10">
                    Enable
                  </button>
                </div>
                <div>
                  <h3 className="font-medium text-gray-900 dark:text-white mb-4">Active Sessions</h3>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg dark:bg-gray-900">
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">MacBook Pro - Chrome</p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">Current session</p>
                      </div>
                      <span className="text-sm text-green-600">Active now</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'equity' && (
            <div className="space-y-6">
              {/* Saved notification */}
              {equitySaved && (
                <div className="rounded-lg bg-green-50 border border-green-200 p-4 dark:bg-green-900/20 dark:border-green-800">
                  <p className="text-green-700 dark:text-green-400 font-medium">Health equity settings saved successfully</p>
                </div>
              )}

              {/* Racial Medicine Awareness */}
              <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-2 rounded-lg bg-pink-100 dark:bg-pink-900/30">
                    <Heart className="h-5 w-5 text-pink-600 dark:text-pink-400" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                      Racial Medicine Awareness
                    </h2>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Helps address the "white default" in medical diagnostics
                    </p>
                  </div>
                </div>
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Fitzpatrick Skin Type
                    </label>
                    <select
                      value={equitySettings.skinType}
                      onChange={(e) => setEquitySettings({ ...equitySettings, skinType: e.target.value })}
                      className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-mdx-primary focus:outline-none focus:ring-1 focus:ring-mdx-primary dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                    >
                      <option value="">Select skin type...</option>
                      {fitzpatrickTypes.map((type) => (
                        <option key={type.value} value={type.value}>{type.label}</option>
                      ))}
                    </select>
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      Enables pulse oximeter accuracy alerts and skin assessment guidance
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Ancestry
                    </label>
                    <select
                      value={equitySettings.ancestry}
                      onChange={(e) => setEquitySettings({ ...equitySettings, ancestry: e.target.value })}
                      className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-mdx-primary focus:outline-none focus:ring-1 focus:ring-mdx-primary dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                    >
                      {ancestryOptions.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      Enables pharmacogenomic medication considerations
                    </p>
                  </div>
                </div>
              </div>

              {/* Cultural Care Preferences */}
              <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
                    <Shield className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                      Cultural & Religious Preferences
                    </h2>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Respect cultural and religious healthcare preferences
                    </p>
                  </div>
                </div>
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Religion
                    </label>
                    <select
                      value={equitySettings.religion}
                      onChange={(e) => setEquitySettings({ ...equitySettings, religion: e.target.value })}
                      className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-mdx-primary focus:outline-none focus:ring-1 focus:ring-mdx-primary dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                    >
                      {religionOptions.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>

                  {/* Blood Product Preferences for JW */}
                  {equitySettings.religion === 'jehovah_witness' && (
                    <div className="p-4 rounded-lg bg-amber-50 border border-amber-200 dark:bg-amber-900/20 dark:border-amber-800">
                      <div className="flex items-center gap-2 mb-3">
                        <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                        <h3 className="font-medium text-amber-800 dark:text-amber-300">Blood Product Preferences</h3>
                      </div>
                      <p className="text-sm text-amber-700 dark:text-amber-400 mb-4">
                        Individual conscience items - check what the patient accepts:
                      </p>
                      <div className="grid grid-cols-2 gap-3">
                        {Object.entries(equitySettings.bloodProductPreferences).map(([key, value]) => (
                          <label key={key} className="flex items-center gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={value}
                              onChange={() => handleBloodPreferenceChange(key as keyof typeof equitySettings.bloodProductPreferences)}
                              className="rounded border-gray-300 text-mdx-primary focus:ring-mdx-primary"
                            />
                            <span className="text-gray-700 dark:text-gray-300">
                              {key === 'wholeBood' ? 'Whole Blood' :
                               key === 'redCells' ? 'Red Cells' :
                               key === 'plasma' ? 'Plasma' :
                               key === 'platelets' ? 'Platelets' :
                               key === 'albumin' ? 'Albumin' :
                               key === 'immunoglobulins' ? 'Immunoglobulins' :
                               'Cell Salvage'}
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Dietary Restrictions
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      {dietaryOptions.map((option) => (
                        <label key={option} className="flex items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={equitySettings.dietaryRestrictions.includes(option)}
                            onChange={() => handleDietaryChange(option)}
                            className="rounded border-gray-300 text-mdx-primary focus:ring-mdx-primary"
                          />
                          <span className="text-gray-700 dark:text-gray-300">{option}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center justify-between py-2">
                    <div>
                      <h3 className="font-medium text-gray-900 dark:text-white">Same-Gender Provider Preference</h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Request same-gender provider for examinations</p>
                    </div>
                    <button
                      onClick={() => setEquitySettings({ ...equitySettings, sameGenderProvider: !equitySettings.sameGenderProvider })}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        equitySettings.sameGenderProvider ? 'bg-mdx-primary' : 'bg-gray-300 dark:bg-gray-600'
                      }`}
                    >
                      <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
                        equitySettings.sameGenderProvider ? 'translate-x-6' : 'translate-x-1'
                      }`} />
                    </button>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Decision-Making Style
                    </label>
                    <select
                      value={equitySettings.decisionMakingStyle}
                      onChange={(e) => setEquitySettings({ ...equitySettings, decisionMakingStyle: e.target.value })}
                      className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-mdx-primary focus:outline-none focus:ring-1 focus:ring-mdx-primary dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                    >
                      <option value="individual">Individual (patient decides alone)</option>
                      <option value="family_centered">Family-Centered (family involved in decisions)</option>
                      <option value="patriarch_led">Patriarch-Led (senior male makes decisions)</option>
                      <option value="shared">Shared (collaborative with family)</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Maternal Health */}
              <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-2 rounded-lg bg-rose-100 dark:bg-rose-900/30">
                    <Baby className="h-5 w-5 text-rose-600 dark:text-rose-400" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                      Maternal Health Status
                    </h2>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Enables high-risk OB monitoring and alerts
                    </p>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Maternal Status
                  </label>
                  <select
                    value={equitySettings.maternalStatus}
                    onChange={(e) => setEquitySettings({ ...equitySettings, maternalStatus: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-mdx-primary focus:outline-none focus:ring-1 focus:ring-mdx-primary dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                  >
                    <option value="">Not applicable</option>
                    <option value="pregnant">Currently Pregnant</option>
                    <option value="postpartum">Postpartum (within 12 months)</option>
                  </select>
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Black women face 3-4x higher maternal mortality risk - enables enhanced monitoring
                  </p>
                </div>
              </div>

              {/* Implicit Bias Alerts */}
              <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800">
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
                    <AlertTriangle className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                      Implicit Bias Awareness
                    </h2>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Gentle reminders during clinical documentation
                    </p>
                  </div>
                </div>
                <div className="flex items-center justify-between py-2">
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">Enable Bias Awareness Alerts</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Non-accusatory prompts during pain assessment, prescribing, and triage
                    </p>
                  </div>
                  <button
                    onClick={() => setEquitySettings({ ...equitySettings, biasAlertsEnabled: !equitySettings.biasAlertsEnabled })}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      equitySettings.biasAlertsEnabled ? 'bg-mdx-primary' : 'bg-gray-300 dark:bg-gray-600'
                    }`}
                  >
                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
                      equitySettings.biasAlertsEnabled ? 'translate-x-6' : 'translate-x-1'
                    }`} />
                  </button>
                </div>
              </div>

              {/* Save Button */}
              <div className="flex justify-end">
                <button
                  onClick={saveEquitySettings}
                  className="inline-flex items-center gap-2 rounded-lg bg-mdx-primary px-6 py-2 text-sm font-medium text-white hover:bg-mdx-primary/90 transition-colors"
                >
                  <Save className="h-4 w-4" />
                  Save Health Equity Settings
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
