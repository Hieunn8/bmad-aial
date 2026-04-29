local cjson = require("cjson.safe")
local http = require("resty.http")

local function b64url_decode(input)
  local s = input:gsub("-", "+"):gsub("_", "/")
  local pad = #s % 4
  if pad == 2 then
    s = s .. "=="
  elseif pad == 3 then
    s = s .. "="
  elseif pad ~= 0 then
    return nil
  end
  return ngx.decode_base64(s)
end

return function()
  local auth_header = kong.request.get_header("authorization")
  if not auth_header then
    return
  end

  local _, _, token = auth_header:find("^[Bb]earer%s+(.+)$")
  if not token then
    return
  end

  local parts = {}
  for part in token:gmatch("[^%.]+") do
    parts[#parts + 1] = part
  end

  if #parts < 2 then
    return kong.response.exit(401, { message = "Invalid token payload" })
  end

  local payload_json = b64url_decode(parts[2])
  if not payload_json then
    return kong.response.exit(401, { message = "Invalid token payload" })
  end

  local claims = cjson.decode(payload_json)
  if not claims then
    return kong.response.exit(401, { message = "Invalid token payload" })
  end

  local principal_roles = claims.roles
  if type(principal_roles) == "string" then
    principal_roles = { principal_roles }
  end
  if type(principal_roles) ~= "table" then
    principal_roles = {}
  end

  local cerbos_payload = {
    requestId = string.format("%s:%s:%s", claims.sub or "unknown", "api:chat", "query"),
    principal = {
      id = claims.sub or "",
      roles = principal_roles,
      attr = {
        department = claims.department or "",
        clearance = tostring(claims.clearance or ""),
      },
    },
    resources = {
      {
        resource = {
          kind = "api:chat",
          id = "default",
        },
        actions = { "query" },
      },
    },
  }

  local httpc = http.new()
  httpc:set_timeout(5000)

  local res, err = httpc:request_uri("http://cerbos:3592/api/check/resources", {
    method = "POST",
    body = cjson.encode(cerbos_payload),
    headers = {
      ["Content-Type"] = "application/json",
    },
  })

  if not res then
    kong.log.err("Cerbos request failed: ", err or "unknown error")
    return kong.response.exit(503, { message = "Authorization service unavailable" })
  end

  if res.status >= 400 then
    kong.log.err("Cerbos returned status ", res.status, ": ", res.body or "")
    return kong.response.exit(503, { message = "Authorization service unavailable" })
  end

  local result = cjson.decode(res.body or "")
  local effect = result
    and result.results
    and result.results[1]
    and result.results[1].actions
    and result.results[1].actions.query

  if effect ~= "EFFECT_ALLOW" then
    return kong.response.exit(403, { message = "Access denied" })
  end
end
