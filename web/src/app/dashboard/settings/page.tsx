'use client';

import { useState } from 'react';
import { Save, User, Bell, Shield, Database, Mic } from 'lucide-react';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('profile');

  const tabs = [
    { id: 'profile', name: 'Profile', icon: User },
    { id: 'notifications', name: 'Notifications', icon: Bell },
    { id: 'security', name: 'Security', icon: Shield },
    { id: 'integrations', name: 'EHR Integrations', icon: Database },
    { id: 'transcription', name: 'Transcription', icon: Mic },
  ];

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
        </div>
      </div>
    </div>
  );
}
