import { afterEach, expect, it, vi } from "vitest";

import { request } from "./client";

afterEach(() => vi.unstubAllGlobals());

it("does not send a JSON content type for read-only requests", async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true })));
  vi.stubGlobal("fetch", fetchMock);

  await request("/employees");

  const headers = new Headers(fetchMock.mock.calls[0][1].headers);
  expect(headers.has("Content-Type")).toBe(false);
});

it("sets a JSON content type for requests with a body", async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true })));
  vi.stubGlobal("fetch", fetchMock);

  await request("/employees", { method: "POST", body: JSON.stringify({ name: "Ada" }) });

  const headers = new Headers(fetchMock.mock.calls[0][1].headers);
  expect(headers.get("Content-Type")).toBe("application/json");
});
