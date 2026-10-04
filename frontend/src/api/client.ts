import createClient from "openapi-fetch";
import type { paths } from "./schema";

export const api = createClient<paths>({
  baseUrl: "",
  headers: {
    "X-Requested-With": "XMLHttpRequest",
  },
});

export type ApiPaths = paths;