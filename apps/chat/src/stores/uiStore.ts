/**
 * uiStore — Sidebar, modal, theme state (Zustand slice)
 * Architecture: §ST-2 stores/uiStore.ts
 */
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

interface UIStore {
  /** Sidebar collapsed state */
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;

  /** Active modal */
  activeModal: string | null;
  openModal: (modalId: string) => void;
  closeModal: () => void;

  /** Connection status */
  isOnline: boolean;
  setOnline: (online: boolean) => void;
}

export const useUIStore = create<UIStore>()(
  devtools(
    persist(
      (set) => ({
        isSidebarOpen: true,
        toggleSidebar: () =>
          set(
            (state) => ({ isSidebarOpen: !state.isSidebarOpen }),
            false,
            'ui/toggleSidebar',
          ),
        setSidebarOpen: (open) =>
          set({ isSidebarOpen: open }, false, 'ui/setSidebarOpen'),

        activeModal: null,
        openModal: (modalId) =>
          set({ activeModal: modalId }, false, 'ui/openModal'),
        closeModal: () =>
          set({ activeModal: null }, false, 'ui/closeModal'),

        isOnline: true,
        setOnline: (online) =>
          set({ isOnline: online }, false, 'ui/setOnline'),
      }),
      {
        name: 'aial-ui-store',
        partialize: (state) => ({ isSidebarOpen: state.isSidebarOpen }),
      },
    ),
    { name: 'UIStore' },
  ),
);
