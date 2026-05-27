// Root path — middleware handles redirect to /login or /dashboard
// This page is never directly rendered.
import { redirect } from 'next/navigation';

export default function RootPage() {
  redirect('/dashboard');
}
