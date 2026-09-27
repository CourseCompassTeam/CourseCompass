// AuthService implementations from the Chat Class Diagram.
//
// AuthService interface:
//   getSessionToken() -> Promise<string>
//   getUserId() -> string

/** AuthService backed by Clerk's useAuth() values. */
export class ClerkAuthService {
  /**
   * @param {{getToken: () => Promise<string|null>, userId: ?string}} auth
   *     The getToken function and userId from Clerk's useAuth().
   */
  constructor({ getToken, userId }) {
    this._getToken = getToken;
    this._userId = userId;
  }

  async getSessionToken() {
    return (await this._getToken()) ?? '';
  }

  getUserId() {
    return this._userId ?? '';
  }
}

/** Fake signed-in user, for local development without a Clerk key. */
export class DevAuthService {
  async getSessionToken() {
    return 'dev-token';
  }

  getUserId() {
    return 'dev-user';
  }
}
