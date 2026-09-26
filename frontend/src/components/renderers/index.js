// MessageRenderer registry (Strategy pattern).
//
// Every renderer takes a { message } prop and returns the bubble for one
// message type. To support a new response type, add a renderer and register
// it here. ChatContainer and ChatService don't change (Open/Closed).

import { MessageType } from '../../models/message.js';
import AuditMessageRenderer from './AuditMessageRenderer.jsx';
import ErrorMessageRenderer from './ErrorMessageRenderer.jsx';
import QueryMessageRenderer from './QueryMessageRenderer.jsx';
import RecommendationMessageRenderer from
  './RecommendationMessageRenderer.jsx';
import RedirectMessageRenderer from './RedirectMessageRenderer.jsx';

const RENDERERS = {
  [MessageType.QUERY]: QueryMessageRenderer,
  [MessageType.AUDIT]: AuditMessageRenderer,
  [MessageType.RECOMMENDATION]: RecommendationMessageRenderer,
  [MessageType.REDIRECT]: RedirectMessageRenderer,
  [MessageType.ERROR]: ErrorMessageRenderer,
};

/** Returns the renderer component for a message type. */
export function getRenderer(type) {
  return RENDERERS[type] ?? ErrorMessageRenderer;
}
