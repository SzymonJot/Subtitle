import Home from "../../pages/Home";
import { createClient } from "@/lib/server";
import { redirect, type LoaderFunctionArgs } from "react-router";

// Loader to enforce authentication
export const loader = async ({ request }: LoaderFunctionArgs) => {
    const { supabase } = createClient(request);
    const { data, error } = await supabase.auth.getUser();
    if (error || !data?.user) {
        return redirect("/login");
    }
    return null;
};

export default function Index() {
    return <Home />;
}
