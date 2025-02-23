# API Connector

`api_client` est une bibliothèque Python conçue pour faciliter la connexion à un service web API. Elle utilise `aiohttp` pour gérer les requêtes HTTP de manière asynchrone, ce qui la rend idéale pour les applications nécessitant des performances élevées et une gestion efficace des connexions simultanées.

## Fonctionnalités

- **Connexion asynchrone** : Utilise `aiohttp` pour des requêtes HTTP non bloquantes.
- **Facile à utiliser** : API simple et intuitive pour intégrer rapidement dans vos projets.
- **Support des WebSockets** : Idéal pour les applications en temps réel.
- **Gestion des sessions** : Support des cookies et des en-têtes personnalisés.

## Installation

Pour installer `api_client`, utilisez pip :

```bash
pip install api_client
```

## Utilisation

Voici un exemple de base pour utiliser `api_client` dans votre projet :

```python
import asyncio


async def main():
    # Initialisez le connecteur avec l'URL de base de votre API
    client = APIClient(base_url="https://api.example.com")

    # Effectuez une requête GET asynchrone
    response = await client.login(username="", password="")
    data = await response.json()
    print(data)


# Exécutez la fonction principale
asyncio.run(main())
```

## Configuration

Vous pouvez configurer `APIConnector` avec différentes options :

- `base_url` : L'URL de base de votre API.
- `headers` : En-têtes HTTP personnalisés.
- `timeout` : Délai d'attente pour les requêtes.

```python
client = APIClient(
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    timeout=10
)
```

## Contribution

Les contributions sont les bienvenues ! Pour contribuer :

1. Forkez le dépôt.
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/new-feature`).
3. Commitez vos modifications (`git commit -am 'Add new feature'`).
4. Poussez vers la branche (`git push origin feature/new-feature`).
5. Ouvrez une Pull Request.

## Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## Contact

Pour toute question ou suggestion, n'hésitez pas à ouvrir une issue ou à contacter l'auteur.
