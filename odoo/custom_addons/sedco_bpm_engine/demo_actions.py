def ok(env, ctx):
    proc_id = ctx.get('proc_id')
    if proc_id:
        proc = env['bpm.process.instance'].browse(proc_id)
        if proc.exists():
            proc.message_post(body='System action OK executed with ctx: %s' % ctx)
    return True
