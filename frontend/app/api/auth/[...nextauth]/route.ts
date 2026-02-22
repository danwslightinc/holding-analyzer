import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";

const allowedEmails = process.env.ALLOWED_EMAILS
    ? process.env.ALLOWED_EMAILS.split(",").map(e => e.trim().toLowerCase())
    : [];

const handler = NextAuth({
    providers: [
        GoogleProvider({
            clientId: process.env.GOOGLE_CLIENT_ID || "",
            clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
        }),
    ],
    secret: process.env.NEXTAUTH_SECRET,
    callbacks: {
        async signIn({ user, account, profile }) {
            if (!user.email) return false;

            // If ALLOWED_EMAILS is not configured at all, we allow anyone for now, 
            // but it's much safer to enforce explicitly.
            if (process.env.ALLOWED_EMAILS) {
                if (!allowedEmails.includes(user.email.toLowerCase())) {
                    return false; // Access Denied
                }
            }
            return true;
        },
    },
    pages: {
        signIn: '/login', // We will create a custom login page
    }
});

export { handler as GET, handler as POST };
