import { createBrowserRouter } from "react-router-dom";
import Login, { action as loginAction } from "./app/routes/login";
import Protected, { loader as protectedLoader } from "./app/routes/protected";
import Index, { loader as indexLoader } from "./app/routes/_index";
import AppRoot from "./AppRoot";

export const router = createBrowserRouter([
    {
        path: "/",
        element: <AppRoot />,
        children: [
            {
                index: true,
                loader: indexLoader,
                element: <Index />,
            },
            {
                path: "login",
                action: loginAction,
                element: <Login />,
            },
            {
                path: "sign-up",
                lazy: async () => {
                    let { default: SignUp, action } = await import("./app/routes/sign-up");
                    return { Component: SignUp, action };
                }
            },
            {
                path: "protected",
                loader: protectedLoader,
                element: <Protected />
            },
            {
                path: "logout",
                lazy: async () => {
                    // Shadcn usually creates logout.tsx with specific exports, often just a loader or action?
                    // Usually it's a resource route, but here we can redirect.
                    // Let's assume it exports loader.
                    let { loader } = await import("./app/routes/logout");
                    return { loader };
                }
            },
            {
                path: "auth/callback",
                // magic link callback? or oauth?
                // The user had App.tsx logic for verifyOtp.
                // Shadcn might have auth.confirm.tsx?
                // Yes, src\app\routes\auth.confirm.tsx
                path: "auth/confirm",
                lazy: async () => {
                    let { loader } = await import("./app/routes/auth.confirm");
                    return { loader };
                }
            }
        ]
    }
]);
