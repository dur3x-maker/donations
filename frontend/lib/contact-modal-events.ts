export const OPEN_CONTACT_MODAL_EVENT = "tipfortea:open-contact-modal";

export function openContactModal() {
  window.dispatchEvent(new Event(OPEN_CONTACT_MODAL_EVENT));
}
