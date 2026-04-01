declare global {
  interface Window {
    audioProcDesktop?: {
      isDesktop: boolean;
      platform: string;
      backendUrl: string;
      chooseFolder: () => Promise<string | null>;
      showItemInFolder: (absolutePath: string) => Promise<boolean>;
    };
  }
}

export {};
