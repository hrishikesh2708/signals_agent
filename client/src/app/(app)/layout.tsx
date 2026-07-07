export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <div className="h-full min-h-screen">{children}</div>;
}
