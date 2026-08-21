"use client";

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { User, UserRole } from '@/types';
import { authApi } from '@/lib/api';

interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  _hydrated: boolean;

  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  isRole: (role: UserRole) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
      isLoading: false,
      isAuthenticated: false,
      _hydrated: false,

      login: async (email: string, password: string) => {
        set({ isLoading: true });
        try {
          const res = await authApi.login({ email, password });
          const { access_token, refresh_token } = res.data;
          set({ token: access_token, refreshToken: refresh_token, isAuthenticated: true });
          await get().fetchUser();
        } catch (err) {
          throw err;
        } finally {
          set({ isLoading: false });
        }
      },

      logout: () => {
        set({ user: null, token: null, refreshToken: null, isAuthenticated: false });
      },

      fetchUser: async () => {
        try {
          const res = await authApi.getMe();
          set({ user: res.data, isAuthenticated: true });
        } catch {
          // Don't logout on failure - might be temporary
        }
      },

      isRole: (role: UserRole) => get().user?.role === role,
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => {
        return (state) => {
          if (state) {
            state._hydrated = true;
          }
        };
      },
    }
  )
);
