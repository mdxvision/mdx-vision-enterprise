'use client';

import { useState } from 'react';
import { Plus, Search, Filter, User, MoreVertical } from 'lucide-react';
import Link from 'next/link';

const mockPatients = [
  {
    id: '1',
    mrn: 'MRN-001234',
    firstName: 'John',
    lastName: 'Smith',
    dateOfBirth: '1965-03-15',
    gender: 'MALE',
    email: 'john.smith@email.com',
    phone: '(555) 123-4567',
    lastVisit: '2024-01-15',
    totalEncounters: 12,
  },
  {
    id: '2',
    mrn: 'MRN-005678',
    firstName: 'Sarah',
    lastName: 'Johnson',
    dateOfBirth: '1978-07-22',
    gender: 'FEMALE',
    email: 'sarah.j@email.com',
    phone: '(555) 234-5678',
    lastVisit: '2024-01-14',
    totalEncounters: 8,
  },
  {
    id: '3',
    mrn: 'MRN-009012',
    firstName: 'Michael',
    lastName: 'Brown',
    dateOfBirth: '1952-11-08',
    gender: 'MALE',
    email: 'mbrown@email.com',
    phone: '(555) 345-6789',
    lastVisit: '2024-01-13',
    totalEncounters: 24,
  },
];

export default function PatientsPage() {
  const [searchQuery, setSearchQuery] = useState('');

  const calculateAge = (dob: string) => {
    const birthDate = new Date(dob);
    const today = new Date();
    let age = today.getFullYear() - birthDate.getFullYear();
    const monthDiff = today.getMonth() - birthDate.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    return age;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Patients
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage patient records and history
          </p>
        </div>
        <Link
          href="/dashboard/patients/new"
          className="inline-flex items-center gap-2 rounded-lg bg-mdx-primary px-4 py-2 text-sm font-medium text-white hover:bg-mdx-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Add Patient
        </Link>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search by name or MRN..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-gray-300 bg-white py-2 pl-10 pr-4 text-sm focus:border-mdx-primary focus:outline-none focus:ring-1 focus:ring-mdx-primary dark:border-gray-700 dark:bg-gray-800 dark:text-white"
          />
        </div>
        <button className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700">
          <Filter className="h-4 w-4" />
          Filters
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {mockPatients.map((patient) => (
          <Link
            key={patient.id}
            href={'/dashboard/patients/' + patient.id}
            className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 hover:shadow-md transition-shadow dark:bg-gray-800 dark:ring-gray-800"
          >
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-mdx-primary/10">
                <User className="h-6 w-6 text-mdx-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-gray-900 dark:text-white truncate">
                  {patient.firstName} {patient.lastName}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {patient.mrn}
                </p>
              </div>
              <button className="p-1 text-gray-400 hover:text-gray-600">
                <MoreVertical className="h-5 w-5" />
              </button>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-gray-500 dark:text-gray-400">Age</p>
                <p className="font-medium text-gray-900 dark:text-white">
                  {calculateAge(patient.dateOfBirth)} years
                </p>
              </div>
              <div>
                <p className="text-gray-500 dark:text-gray-400">Gender</p>
                <p className="font-medium text-gray-900 dark:text-white">
                  {patient.gender}
                </p>
              </div>
              <div>
                <p className="text-gray-500 dark:text-gray-400">Last Visit</p>
                <p className="font-medium text-gray-900 dark:text-white">
                  {new Date(patient.lastVisit).toLocaleDateString()}
                </p>
              </div>
              <div>
                <p className="text-gray-500 dark:text-gray-400">Encounters</p>
                <p className="font-medium text-gray-900 dark:text-white">
                  {patient.totalEncounters}
                </p>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
