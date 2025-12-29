/**
 * Authentication State Store using Zustand
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role: string;
  vertical: string;
  organizationId?: string;
  epicProviderId?: string;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  
  // Actions
  setUser: (user: User) => void;
  setTokens: (access: string, refresh: string) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,

      setUser: (user) => set({ user, isAuthenticated: true }),
      
      setTokens: (access, refresh) => set({ 
        accessToken: access, 
        refreshToken: refresh,
        isAuthenticated: true 
      }),
      
      logout: () => set({ 
        user: null, 
        accessToken: null, 
        refreshToken: null, 
        isAuthenticated: false 
      }),
      
      setLoading: (loading) => set({ isLoading: loading }),
    }),
    {
      name: 'mdx-auth-storage',
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({ 
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
