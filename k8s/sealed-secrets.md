<div style="background-color: #f6f3fb; border-left: 4px solid #7c5cff; padding: 16px; margin: 16px 0;">
 
  
 
<h1 style="margin: 0;">What are Sealed Secrets and why do you need them</h1>
 
  
 
</div>
 
  
 
Sealed Secrets are Kubernetes secrets but encrypted so they can safely live in Git. Without them you have a problem: Fleet deploys from Git, but secrets cannot go into Git as plain Kubernetes secrets. A plain Kubernetes secret is just base64 encoded — and base64 is not encryption. It is just encoding. Anyone can reverse it instantly:
 
  
```
    echo "c3VwZXJzZWNyZXQ=" | base64 -d
```
 
    # supersecret
 
  
 
Anyone with repo access can read every secret value. That is not acceptable.
 
Sealed Secrets solves this by installing a controller in the cluster that holds a private key. You use the `kubeseal` CLI to encrypt your secret with the public key before committing to Git. The encrypted blob is meaningless to anyone without the private key. Only that specific cluster's controller can decrypt it.
 
  
 
* * *
 
  
 
<div style="background-color: #f6f3fb; border-left: 4px solid #7c5cff; padding: 16px; margin: 16px 0;">
 
  
 
<h1 style="margin: 0;">How it works — the key concept</h1>
 
  
 
</div>
 
  
 
Sealed Secrets uses <strong>asymmetric encryption</strong> (RSA):
 
<ol>
 
<li>The controller runs in the cluster and generates a public/private key pair</li>
 
<li>You use <code>kubeseal</code> with the <strong>public key</strong> to encrypt your secret locally</li>
 
<li>The result is a <code>SealedSecret</code> — an encrypted blob safe to commit to Git</li>
 
<li>Fleet deploys it to the cluster</li>
 
<li>The controller uses the <strong>private key</strong> to decrypt it back into a real Kubernetes Secret</li>
 
<li>Your application reads the normal Kubernetes Secret as usual</li>
 
</ol>
 
The public key can only encrypt — it cannot decrypt. Only the controller with the private key can open it. You can share the public key freely. The private key never leaves the cluster.
 
  
 
* * *
 
  
 
<div style="background-color: #f6f3fb; border-left: 4px solid #7c5cff; padding: 16px; margin: 16px 0;">
 
  
 
<h1 style="margin: 0;">Step 1 — Install the controller via Fleet</h1>
 
  
 
</div>
 
  
 
The controller is deployed as a Helm chart via Fleet. Add this to your Git repo:
 
<strong>sealed-secrets/fleet.yaml:</strong>
 
  
 
<pre style="background-color:#f0f0f0;padding:16px;border-radius:4px;font-family:monospace;font-size:1rem;font-weight:700;color:#1a1a1a;overflow-x:auto;white-space:pre;">
 
defaultNamespace: kube-system
 
helm:
 
  releaseName: sealed-secrets
 
  repo: https://bitnami-labs.github.io/sealed-secrets
 
  chart: sealed-secrets
 
  version: "2.16.2"
 
targetCustomizations:
 
- name: all-clusters
 
  clusterSelector: {}
 
</pre>
 
  
 
This is Fleet deploying a Helm chart directly — no separate helmrelease.yaml needed. Push to Git, Fleet picks it up, controller deploys to all clusters.
 
Verify the controller is running:
 
  
 
<pre style="background-color:#f0f0f0;padding:16px;border-radius:4px;font-family:monospace;font-size:1rem;font-weight:700;color:#1a1a1a;overflow-x:auto;white-space:pre;">kubectl get pods -n kube-system | grep sealed</pre>
 
  
 
* * *
 
  
 
<div style="background-color: #f6f3fb; border-left: 4px solid #7c5cff; padding: 16px; margin: 16px 0;">
 
  
 
<h1 style="margin: 0;">Step 2 — Install kubeseal CLI</h1>
 
  
 
</div>
 
  
 
<pre style="background-color:#f0f0f0;padding:16px;border-radius:4px;font-family:monospace;font-size:1rem;font-weight:700;color:#1a1a1a;overflow-x:auto;white-space:pre;">
 
wget https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.27.0/kubeseal-0.27.0-linux-amd64.tar.gz
 
tar -xvzf kubeseal-0.27.0-linux-amd64.tar.gz
 
sudo install -m 755 kubeseal /usr/local/bin/kubeseal
 
kubeseal --version
 
</pre>
 
  
 
* * *
 
  
 
<div style="background-color: #f6f3fb; border-left: 4px solid #7c5cff; padding: 16px; margin: 16px 0;">
 
  
 
<h1 style="margin: 0;">Step 3 — Create and seal a secret</h1>
 
  
 
</div>
 
  
 
This is the critical part. The unencrypted secret must <strong>never touch the cluster and never be committed to Git</strong>. The <code>--dry-run=client</code> flag is what makes this safe — it generates the secret YAML locally without applying it to the cluster at all.
 
  
 
<pre style="background-color:#f0f0f0;padding:16px;border-radius:4px;font-family:monospace;font-size:1rem;font-weight:700;color:#1a1a1a;overflow-x:auto;white-space:pre;">
 
# Step 1 — generate the secret locally, NEVER applied to the cluster
 
kubectl create secret generic my-app-secret \
 
  --from-literal=username=admin \
 
  --from-literal=password=supersecret123 \
 
  --dry-run=client -o yaml > /tmp/my-app-secret.yaml
 
  
 
# Step 2 — encrypt it with kubeseal using the controller's public key
 
kubeseal --controller-name=sealed-secrets \
 
  --controller-namespace=kube-system \
 
  --format yaml \
 
  &lt; /tmp/my-app-secret.yaml \
 
  > ~/sealed-secret.yaml
 
  
 
# Step 3 — look at the encrypted output (this is safe to commit)
 
cat ~/sealed-secret.yaml
 
  
 
# Step 4 — clean up the plaintext file
 
rm /tmp/my-app-secret.yaml
 
</pre>
 
  
 
The output is a <code>SealedSecret</code> CRD with encrypted blobs for each value. It looks like unreadable garbage — that is the point. Commit <code>sealed-secret.yaml</code> to Git.
 
  
 
* * *
 
  
 
<div style="background-color: #f6f3fb; border-left: 4px solid #7c5cff; padding: 16px; margin: 16px 0;">
 
  
 
<h1 style="margin: 0;">Step 4 — Deploy via Fleet</h1>
 
  
 
</div>
 
  
 
Add to your Git repo alongside a <code>fleet.yaml</code>:
 
  
 
<pre style="background-color:#f0f0f0;padding:16px;border-radius:4px;font-family:monospace;font-size:1rem;font-weight:700;color:#1a1a1a;overflow-x:auto;white-space:pre;">
 
sealed-secrets-demo/
 
├── fleet.yaml
 
└── sealed-secret.yaml    ← the encrypted output from kubeseal
 
</pre>
 
  
 
Fleet deploys it → controller decrypts it → real Kubernetes Secret appears in the cluster.
 
  
 
* * *
 
  
 
<div style="background-color: #f6f3fb; border-left: 4px solid #7c5cff; padding: 16px; margin: 16px 0;">
 
  
 
<h1 style="margin: 0;">Verifying it worked</h1>
 
  
 
</div>
 
  
 
<pre style="background-color:#f0f0f0;padding:16px;border-radius:4px;font-family:monospace;font-size:1rem;font-weight:700;color:#1a1a1a;overflow-x:auto;white-space:pre;">
 
# Check the SealedSecret was deployed
 
kubectl get sealedsecret -n default
 
  
 
# Check the real secret was created by the controller
 
kubectl get secret my-app-secret -n default
 
  
 
# Verify the actual value decrypted correctly
 
kubectl get secret my-app-secret -n default \
 
  -o jsonpath='{.data.password}' | base64 -d
 
# should print: supersecret123
 
</pre>
 
  
 
<code>-o jsonpath='{.data.password}'</code> pulls out just the password field. Kubernetes stores it base64 encoded, so you pipe it to <code>base64 -d</code> to read the plaintext. If it prints the correct value — the whole pipeline worked.
 
  
 
* * *
 
  
 
<div style="background-color: #f6f3fb; border-left: 4px solid #7c5cff; padding: 16px; margin: 16px 0;">
 
  
 
<h1 style="margin: 0;">Step 5 — Using the secret in your application</h1>
 
  
 
</div>
 
  
 
Once the controller has decrypted the <code>SealedSecret</code> into a real Kubernetes Secret, your application consumes it exactly like any other Kubernetes Secret. The application never knows anything about Sealed Secrets — it just reads a normal secret. There are two ways to do this.
 
  
 
<h2>Option A — Environment variables (most common)</h2>
 
  
 
Inject each secret key as an environment variable in your container. This is the most common pattern for database passwords, API keys, and credentials.
 
  
 
<pre style="background-color:#f0f0f0;padding:16px;border-radius:4px;font-family:monospace;font-size:1rem;font-weight:700;color:#1a1a1a;overflow-x:auto;white-space:pre;">
 
apiVersion: apps/v1
 
kind: Deployment
 
metadata:
 
  name: my-app
 
  namespace: default
 
spec:
 
  replicas: 1
 
  selector:
 
    matchLabels:
 
      app: my-app
 
  template:
 
    metadata:
 
      labels:
 
        app: my-app
 
    spec:
 
      containers:
 
        - name: my-app
 
          image: my-app:latest
 
          env:
 
            # Inject the username key from the secret
 
            - name: APP_USERNAME
 
              valueFrom:
 
                secretKeyRef:
 
                  name: my-app-secret   # must match the name in your sealed-secret.yaml
 
                  key: username
 
            # Inject the password key from the secret
 
            - name: APP_PASSWORD
 
              valueFrom:
 
                secretKeyRef:
 
                  name: my-app-secret
 
                  key: password
 
</pre>
 
  
 
Inside the container, <code>APP_USERNAME</code> will be <code>admin</code> and <code>APP_PASSWORD</code> will be <code>supersecret123</code> — as plain strings, no base64. Your application code reads them with <code>os.environ["APP_PASSWORD"]</code> or equivalent.
 
  
 
You can also pull in every key from a secret at once using <code>envFrom</code>:
 
  
 
<pre style="background-color:#f0f0f0;padding:16px;border-radius:4px;font-family:monospace;font-size:1rem;font-weight:700;color:#1a1a1a;overflow-x:auto;white-space:pre;">
 
      containers:
 
        - name: my-app
 
          image: my-app:latest
 
          envFrom:
 
            - secretRef:
 
                name: my-app-secret   # all keys become env vars
 
</pre>
 
  
 
With <code>envFrom</code>, both <code>username</code> and <code>password</code> become environment variables automatically, using the secret key names as-is.
 
  
 
<h2>Option B — Volume mount (for files, TLS certs, config files)</h2>
 
  
 
Mount the secret as files inside the container. Each key in the secret becomes a file, with the value as its contents. Use this pattern when your application expects credentials as files on disk — for example, TLS certificates, SSH keys, or <code>.env</code> files.
 
  
 
<pre style="background-color:#f0f0f0;padding:16px;border-radius:4px;font-family:monospace;font-size:1rem;font-weight:700;color:#1a1a1a;overflow-x:auto;white-space:pre;">
 
apiVersion: apps/v1
 
kind: Deployment
 
metadata:
 
  name: my-app
 
  namespace: default
 
spec:
 
  replicas: 1
 
  selector:
 
    matchLabels:
 
      app: my-app
 
  template:
 
    metadata:
 
      labels:
 
        app: my-app
 
    spec:
 
      containers:
 
        - name: my-app
 
          image: my-app:latest
 
          volumeMounts:
 
            - name: app-secret-volume
 
              mountPath: /etc/my-app/secrets   # directory inside the container
 
              readOnly: true
 
      volumes:
 
        - name: app-secret-volume
 
          secret:
 
            secretName: my-app-secret   # must match the name in your sealed-secret.yaml
 
</pre>
 
  
 
Inside the container, the secret keys become files:
 
  
 
<pre style="background-color:#f0f0f0;padding:16px;border-radius:4px;font-family:monospace;font-size:1rem;font-weight:700;color:#1a1a1a;overflow-x:auto;white-space:pre;">
 
/etc/my-app/secrets/
 
├── username    # contains: admin
 
└── password    # contains: supersecret123
 
</pre>
 
  
 
Your application reads them as normal files: <code>open("/etc/my-app/secrets/password").read()</code> or equivalent.
 
  
 
<h2>Key naming — match the secret name exactly</h2>
 
  
 
The <code>name</code> field in both options (<code>secretKeyRef.name</code> and <code>secretName</code>) must exactly match the <code>metadata.name</code> field in your <code>sealed-secret.yaml</code>. If they do not match, the Pod will fail to start with an <code>InvalidSpec</code> or <code>CreateContainerConfigError</code> error.
 
  
 
Verify the name:
 
  
 
<pre style="background-color:#f0f0f0;padding:16px;border-radius:4px;font-family:monospace;font-size:1rem;font-weight:700;color:#1a1a1a;overflow-x:auto;white-space:pre;">
 
kubectl get secret -n default
 
# NAME             TYPE     DATA   AGE
 
# my-app-secret    Opaque   2      5m
 
</pre>
 
  
 
<h2>Confirming the Pod can read the secret</h2>
 
  
 
<pre style="background-color:#f0f0f0;padding:16px;border-radius:4px;font-family:monospace;font-size:1rem;font-weight:700;color:#1a1a1a;overflow-x:auto;white-space:pre;">
 
# Check the Pod started successfully (no CreateContainerConfigError)
 
kubectl get pod -n default
 
  
 
# Confirm the env var is visible inside the running container
 
kubectl exec -n default deployment/my-app -- env | grep APP_PASSWORD
 
# APP_PASSWORD=supersecret123
 
  
 
# Or for volume mounts
 
kubectl exec -n default deployment/my-app -- cat /etc/my-app/secrets/password
 
# supersecret123
 
</pre>
 
  
 
* * *
 
  
 
<div style="background-color: #f0f7ff; border-left: 4px solid #3b82f6; padding: 12px; margin: 12px 0;">
 
<strong>The complete flow end to end:</strong><br>
 
<code>kubeseal</code> encrypts → Git stores the SealedSecret → Fleet deploys it → controller decrypts it → Kubernetes Secret exists in cluster → Deployment reads it as env vars or files → application gets plain text values
 
</div>
 
  
 
* * *
 
  
 
The answer to "how do you handle secrets in GitOps?"
 
<hr>
 
  
 
<blockquote>"We use Sealed Secrets. The controller runs in the cluster and holds the private key. We use kubeseal to encrypt secrets with the public key before committing to Git. The encrypted blob is meaningless without the private key. Only that specific cluster's controller can decrypt it."</blockquote>
 
  
 
* * *
 
  
 
<div style="background-color: #f6f3fb; border-left: 4px solid #7c5cff; padding: 16px; margin: 16px 0;">
 
  
 
<h1 style="margin: 0;">Problems hit and fixes</h1>
 
  
 
</div>
 
  
 
<h3>kubeseal: service not found</h3>
 
  
 
<strong>Error:</strong> <code>error: cannot get sealed secret service: services "sealed-secrets" not found</code><br>
 
<strong>Cause:</strong> The controller service had a different name than the default kubeseal expects.<br>
 
<strong>Fix:</strong>
 
  
 
<pre style="background-color:#f0f0f0;padding:16px;border-radius:4px;font-family:monospace;font-size:1rem;font-weight:700;color:#1a1a1a;overflow-x:auto;white-space:pre;">kubectl get svc -n kube-system | grep sealed</pre>
 
  
 
Find the actual service name and use it in the <code>--controller-name</code> flag.<br>
 
<strong>Lesson:</strong> Always check the actual service name, never assume defaults.
 
  
 
* * *
 
  
 
<h3>Secret not appearing after Fleet deploys it</h3>
 
  
 
<strong>Symptom:</strong> Fleet shows bundle as active but <code>kubectl get secret my-app-secret -n default</code> returns NotFound.<br>
 
<strong>Debugging:</strong>
 
  
 
<pre style="background-color:#f0f0f0;padding:16px;border-radius:4px;font-family:monospace;font-size:1rem;font-weight:700;color:#1a1a1a;overflow-x:auto;white-space:pre;">
 
# Check if the SealedSecret object even exists
 
kubectl get sealedsecret -n default
 
  
 
# Check controller logs for key rotation messages
 
kubectl logs -n kube-system -l app.kubernetes.io/name=sealed-secrets --tail=20
 
</pre>
 
  
 
<strong>Cause:</strong> The controller was reinstalled and generated a brand new private key. The sealed blob in Git was encrypted with the old public key. The new controller cannot decrypt it — wrong key.<br>
 
<strong>Fix:</strong> Re-seal with the new controller's key:
 
  
 
<pre style="background-color:#f0f0f0;padding:16px;border-radius:4px;font-family:monospace;font-size:1rem;font-weight:700;color:#1a1a1a;overflow-x:auto;white-space:pre;">
 
kubectl create secret generic my-app-secret \
 
  --from-literal=username=admin \
 
  --from-literal=password=supersecret123 \
 
  --dry-run=client -o yaml > /tmp/my-app-secret.yaml
 
  
 
kubeseal --controller-name=sealed-secrets \
 
  --controller-namespace=kube-system \
 
  --format yaml \
 
  &lt; /tmp/my-app-secret.yaml \
 
  > ~/sealed-secret.yaml
 
</pre>
 
  
 
Update <code>sealed-secret.yaml</code> in Git with the new encrypted content. Fleet redeploys → controller decrypts → secret appears.<br>
 
<strong>Lesson:</strong> Each controller instance has a unique private key. If the controller is reinstalled, every sealed secret in Git must be re-sealed with the new public key.
 
  
 
* * *
 
  
 
<div style="background-color: #e85a47ff; border-left: 4px solid #e70d0dff; padding: 12px; margin: 12px 0;">
 
  
 
<strong>CRITICAL — Back up the controller's private key</strong>
 
  
 
</div>
 
  
 
If you lose the controller's private key — reinstall, cluster rebuild, whatever — every sealed secret in your Git repo becomes permanently unreadable. You would have to re-seal everything from scratch.
 
  
 
<pre style="background-color:#f0f0f0;padding:16px;border-radius:4px;font-family:monospace;font-size:1rem;font-weight:700;color:#1a1a1a;overflow-x:auto;white-space:pre;">
 
kubectl get secret -n kube-system \
 
  -l sealedsecrets.bitnami.com/sealed-secrets-key \
 
  -o yaml > sealed-secrets-master-key-backup.yaml
 
</pre>
 
  
 
<strong>Store this somewhere secure. Never in Git.</strong>
 
  
 
* * *
 
  
 
<div style="background-color: #f6f3fb; border-left: 4px solid #7c5cff; padding: 16px; margin: 16px 0;">
 
  
 
<h1 style="margin: 0;">Quick reference</h1>
 
  
 
</div>
 
  
 
<pre style="background-color:#f0f0f0;padding:16px;border-radius:4px;font-family:monospace;font-size:1rem;font-weight:700;color:#1a1a1a;overflow-x:auto;white-space:pre;">
 
# Install kubeseal CLI
 
wget https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.27.0/kubeseal-0.27.0-linux-amd64.tar.gz
 
tar -xvzf kubeseal-0.27.0-linux-amd64.tar.gz
 
sudo install -m 755 kubeseal /usr/local/bin/kubeseal
 
  
 
# Seal a secret
 
kubectl create secret generic my-secret \
 
  --from-literal=key=value \
 
  --dry-run=client -o yaml | \
 
kubeseal --controller-name=sealed-secrets \
 
  --controller-namespace=kube-system \
 
  --format yaml > sealed-secret.yaml
 
  
 
# Verify decryption worked
 
kubectl get secret my-secret -n default \
 
  -o jsonpath='{.data.key}' | base64 -d
 
  
 
# Use in a Deployment (env var)
 
#   env:
 
#     - name: MY_KEY
 
#       valueFrom:
 
#         secretKeyRef:
 
#           name: my-secret
 
#           key: key
 
  
 
# Check controller logs
 
kubectl logs -n kube-system -l app.kubernetes.io/name=sealed-secrets --tail=20
 
  
 
# Back up the master key
 
kubectl get secret -n kube-system \
 
  -l sealedsecrets.bitnami.com/sealed-secrets-key \
 
  -o yaml > sealed-secrets-master-key-backup.yaml
 
</pre>