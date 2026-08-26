import { createTheme, Theme } from '@mui/material';
import { lightTheme } from './light';
import { darkTheme } from './dark';

export function getTheme(mode: 'light' | 'dark'): Theme {
  const themeOptions = mode === 'light' ? lightTheme : darkTheme;
  return createTheme(themeOptions);
}

export { lightTheme, darkTheme };
