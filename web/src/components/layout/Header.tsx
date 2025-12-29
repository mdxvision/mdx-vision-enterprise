'use client';

import { Bell, Search, Menu } from 'lucide-react';

export function Header() {
  return (
    <header className="flex h-16 flex-shrink-0 border-b border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
      <div className="flex flex-1 justify-between px-4 sm:px-6">
        <div className="flex flex-1">
          <button className="px-4 text-gray-500 lg:hidden">
            <Menu className="h-6 w-6" />
          </button>
          <div className="flex w-full max-w-lg items-center">
            <label htmlFor="search" className="sr-only">
              Search
            </label>
            <div className="relative w-full">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                <Search className="h-5 w-5 text-gray-400" />
              </div>
              <input
                id="search"
                name="search"
                className="block w-full rounded-lg border border-gray-300 bg-white py-2 pl-10 pr-3 text-sm placeholder-gray-500 focus:border-mdx-primary focus:outline-none focus:ring-1 focus:ring-mdx-primary dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                placeholder="Search patients, sessions..."
                type="search"
              />
            </div>
          </div>
        </div>
        <div className="ml-4 flex items-center gap-4">
          <button className="relative rounded-full bg-white p-2 text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-mdx-primary focus:ring-offset-2 dark:bg-gray-800">
            <span className="sr-only">View notifications</span>
            <Bell className="h-6 w-6" />
            <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-red-500" />
          </button>
        </div>
      </div>
    </header>
  );
}
