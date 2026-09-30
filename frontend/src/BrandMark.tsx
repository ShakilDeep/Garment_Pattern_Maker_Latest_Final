/** Brand mark: filled long-sleeve shirt closer to REF-004. */
export default function BrandMark({size=52}:{size?:number}){
  return <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
    <path fill="#5b9be0" d="M8 22l10-8 6 5V14l8-6 8 6v5l6-5 10 8-5 8h-5v26c0 2-6 4-14 4s-14-2-14-4V30H13z"/>
    <path fill="#4a8fd4" d="M22 19l10 7 10-7v-5l-10-6-10 6z"/>
    <path fill="#fff" d="M30 26h4v28h-4z" opacity=".9"/>
    <circle cx="32" cy="32" r="1.4" fill="#fff"/><circle cx="32" cy="40" r="1.4" fill="#fff"/>
    <circle cx="32" cy="48" r="1.4" fill="#fff"/>
    <path fill="none" stroke="#d7ebff" strokeWidth="1.2" d="M13 30h-5M51 30h5M18 54h28"/>
  </svg>;
}
