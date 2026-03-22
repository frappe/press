import { onMounted } from "vue";

type Theme = "light" | "dark" | "system";

const getSystemTheme = (): "light" | "dark" => {
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
};

export const setTheme = (name: Theme) => {
  let themeType = name == "system" ? getSystemTheme() : name;
  document.documentElement.setAttribute("data-theme", themeType);
  localStorage.setItem("theme", name);
};

export const initializeTheme = () => {
  onMounted(() => {
    let storedTheme = localStorage.getItem("theme") as Theme || 'system';
    setTheme(storedTheme);

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

    const handleSystemThemeChange = () => {
      if (localStorage.theme === "system") setTheme("system");
    };

    mediaQuery.addEventListener("change", handleSystemThemeChange);

    return () => {
      mediaQuery.removeEventListener("change", handleSystemThemeChange);
    };
  });
};
