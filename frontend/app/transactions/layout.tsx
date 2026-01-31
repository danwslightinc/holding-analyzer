import { Metadata } from "next";

export const metadata: Metadata = {
    title: "Transactions | Dawn's Light Inc",
    description: "Manage portfolio transactions",
};

export default function TransactionsLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return <>{children}</>;
}
