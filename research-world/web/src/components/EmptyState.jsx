export function EmptyState({ icon: Icon, title, detail, action }) {
  return <section className="empty-state">
    {Icon && <Icon size={28} strokeWidth={1.6} />}
    <h2>{title}</h2>
    {detail && <p>{detail}</p>}
    {action}
  </section>;
}
