import { Outlet, ScrollRestoration } from "react-router-dom";
import { AuthProvider } from "./AuthProvider";

export default function AppRoot() {
    return (
        <AuthProvider>
            <Outlet />
            <ScrollRestoration />
        </AuthProvider>
    );
}
