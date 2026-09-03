import { AccountForm } from "@/components/AccountForm";


export default function NewAccountPage() {
  return (
    <div className="page narrowPage">
      <header className="pageHeader formPageHeader">
        <div>
          <span className="eyebrow">New workspace</span>
          <h1>Create account</h1>
          <p>Set the known context. The evidence workflow starts after creation.</p>
        </div>
      </header>
      <AccountForm />
    </div>
  );
}

