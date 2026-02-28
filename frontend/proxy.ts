import { withAuth } from "next-auth/middleware";

export default withAuth({
    pages: {
        signIn: "/login",
    },
});

export const config = {
    // Protect all paths except authentication paths, Next.js internal paths, and static assets
    matcher: ["/((?!login|_next/static|_next/image|favicon.ico|api/auth).*)"],
};
