import { withAuth } from "next-auth/middleware";

export default withAuth({
    pages: {
        signIn: "/login",
    },
    callbacks: {
        authorized: ({ req, token }) => {
            // First check if token exists
            if (!token?.email) return false;

            // Check against allowed emails
            if (process.env.ALLOWED_EMAILS) {
                const allowedEmails = process.env.ALLOWED_EMAILS
                    .split(",")
                    .map(e => e.trim().toLowerCase());

                if (!allowedEmails.includes(token.email.toLowerCase())) {
                    return false;
                }
            }
            return true;
        }
    }
});

export const config = {
    // Protect all paths except authentication paths, Next.js internal paths, and static assets
    matcher: ["/((?!login|health|_next/static|_next/image|favicon.ico|api/auth).*)"],
};
