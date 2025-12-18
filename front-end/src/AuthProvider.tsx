import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { supabase } from './supabaseClient';
import type { Session } from '@supabase/supabase-js';

interface AuthContextType {
    session: Session | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}

interface AuthProviderProps {
    children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
    const [session, setSession] = useState<Session | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        supabase.auth.getSession().then(({ data }: { data: { session: Session | null } }) => {
            setSession(data.session);
            setLoading(false);
        });

        const { data: { subscription } } = supabase.auth.onAuthStateChange(
            (_event, session) => {
                setSession(session);
            }
        );

        return () => subscription.unsubscribe();
    }, []);

    const value = { session };

    return (
        <AuthContext.Provider value={value}>
            {loading ? null : children}
        </AuthContext.Provider>
    );
}
