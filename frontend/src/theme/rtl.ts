import { createTheme, ThemeOptions } from '@mui/material';

export function createRTLTheme(baseTheme: ThemeOptions): ThemeOptions {
  return {
    ...baseTheme,
    direction: 'rtl',
  };
}
