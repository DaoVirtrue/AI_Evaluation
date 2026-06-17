/**
 * @agent-viz/vanilla — Web Components for framework-agnostic integration
 */

class AgentTrajectory extends HTMLElement {
  connectedCallback() {
    this.innerHTML = `<div style="padding:16px;color:#6b7280;">AgentViz Web Component — integrate via &lt;agent-trajectory&gt;</div>`;
  }
}

customElements.define("agent-trajectory", AgentTrajectory);
export { AgentTrajectory };
