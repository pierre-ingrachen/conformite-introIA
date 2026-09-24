<!-- Source : FLI "AI Act Compliance Checker Flowchart" v1.0, 28 juillet 2025 (non affilié à l'UE, pas un avis juridique).
     Format : un fragment = "## id | titre", suivi de lignes "clé: valeur" optionnelles puis du texte. -->

## ai_act.definition | Définition d'un système d'IA (AI Act)
mots-clés: machine learning apprentissage automatique modèle LLM algorithme réseau de neurones
source: AI Act art. 3(1)
Système d'IA : système basé sur une machine, conçu pour fonctionner avec différents niveaux d'autonomie, pouvant faire preuve d'adaptabilité après déploiement, et qui, pour des objectifs explicites ou implicites, déduit à partir des entrées reçues comment générer des sorties (prédictions, contenus, recommandations, décisions) pouvant influencer des environnements physiques ou virtuels. Première question à se poser : le projet est-il un « système d'IA » ? Sinon, l'AI Act ne s'applique pas.

## ai_act.E1 | E1 – Type d'entité (rôle dans la chaîne)
source: art. 3 pts 2-8, considérant 87
Un même acteur peut cumuler plusieurs rôles (considérant 83) : refaire le questionnaire pour chaque rôle.
- Fournisseur (provider) : développe (ou fait développer) un système d'IA ou modèle d'IA à usage général et le met sur le marché / en service sous son nom ou sa marque, payant ou gratuit. → Obligation AI Literacy, puis E2.
- Déployeur (deployer) : utilise un système d'IA sous son autorité (hors usage personnel non professionnel). → AI Literacy, puis E2.
- Distributeur : met un système d'IA à disposition sur le marché de l'Union sans être fournisseur ni importateur. → E2.
- Importateur : établi dans l'UE, met sur le marché un système portant le nom/la marque d'une personne établie hors UE. → E2.
- Fabricant de produit : met sur le marché/en service un système d'IA avec son produit sous son nom/sa marque. → E3.
- Mandataire (authorised representative) : personne établie dans l'UE ayant reçu un mandat écrit d'un fournisseur pour remplir ses obligations. → fin du questionnaire (obligations art. 22 / art. 54).

## ai_act.E2 | E2 – Modifications faisant devenir fournisseur
source: art. 25 pts 1-2
Question : vous (ou un déployeur/distributeur/importateur en aval) faites-vous l'une de ces modifications ? (1) apposer un autre nom/marque sur le système, (2) modifier la destination d'un système déjà en service, (3) modification substantielle (art. 3 pt 23). Si oui : statut « Become a Provider » (vous devenez fournisseur, l'ancien fournisseur doit fournir informations, documentation et accès : « Handover »). Si aucune : passer à HR1.

## ai_act.E3 | E3 – Produit intégrant un système d'IA (fabricant)
source: art. 25 pt 3, annexe I
Le produit intègre-t-il un système d'IA mis sur le marché avec le produit sous le nom du fabricant, ou mis en service sous son nom après la mise sur le marché du produit ? Si oui → HR6. Sinon → hors champ. S'applique uniquement si le produit est mis sur le marché/en service dans l'UE, même si le fabricant est établi hors UE.

## ai_act.HR1 | HR1 – Haut risque : annexe I section B
source: art. 6 pt 1
Le système relève-t-il de l'un de ces domaines (annexe I, section B) : sûreté de l'aviation civile, véhicules à deux/trois roues et quadricycles, véhicules agricoles et forestiers, équipements marins, interopérabilité ferroviaire, véhicules à moteur et remorques, aviation civile ? Si oui : haut risque (fournisseur) / devient fournisseur (autres) puis S1 (règles particulières de ces secteurs). Si aucun : HR2.

## ai_act.HR2 | HR2 – Haut risque : annexe I section A (produits réglementés)
source: art. 6 pt 1
Domaines : machines, jouets, bateaux de plaisance et véhicules nautiques, ascenseurs et composants de sécurité, équipements pour atmosphères explosibles, équipements radio, équipements sous pression, installations à câbles, EPI, appareils à combustion de gaz, dispositifs médicaux, dispositifs médicaux de diagnostic in vitro. Si l'un s'applique → HR3. Sinon → HR4.

## ai_act.HR3 | HR3 – Évaluation de conformité par tiers
source: art. 6 pt 1, art. 43(3)
Le produit (ou celui dont le système d'IA est un « composant de sécurité ») doit-il subir une évaluation de conformité par un tiers selon le droit UE existant (voir annexe I section A) ? Oui → haut risque (fournisseur ; les autres deviennent fournisseur) puis S1. Non → HR4. Certaines lois permettent de s'en dispenser sous les conditions de l'art. 43(3) : répondre Non dans ce cas. En cas de doute, consulter un juriste.

## ai_act.HR4 | HR4 – Haut risque : annexe III (cas d'usage)
mots-clés: recrutement CV candidats tri de candidatures RH évaluation salariés licenciement scoring crédit banque assurance notation élèves examens admission université reconnaissance faciale police justice frontières visa aides sociales urgences secours électricité eau
source: art. 6 pt 2, annexe III
Catégories : biométrie ; infrastructures critiques ; éducation et formation professionnelle ; emploi, gestion des travailleurs et accès au travail indépendant ; accès aux services privés essentiels et services/prestations publics ; répression (law enforcement) ; migration, asile et contrôle aux frontières ; administration de la justice et processus démocratiques. Si l'une s'applique → HR5. Sinon → S1.

## ai_act.HR5 | HR5 – Risque significatif pour santé, sécurité, droits fondamentaux ?
source: art. 6 pt 3
Le système présente-t-il un risque significatif ? NON si au moins une condition : (a) tâche procédurale étroite ; (b) améliore le résultat d'une activité humaine déjà réalisée ; (c) détecte des schémas de décision/écarts sans remplacer ni influencer l'évaluation humaine préalable sans revue humaine appropriée ; (d) tâche préparatoire à une évaluation d'un cas d'usage annexe III. Mais : le profilage de personnes physiques = toujours haut risque (répondre Oui).
Oui → haut risque. Non → le fournisseur doit « Notify NCA » (enregistrement dans la base de données UE avant mise sur le marché, art. 49 pt 2, et documenter l'évaluation, art. 6 pt 4), puis S1.

## ai_act.HR6 | HR6 – Fabricant : composant de sécurité dans un produit réglementé
source: art. 25 pt 3, annexe I
Le produit inclut-il un système d'IA comme « composant de sécurité » (composant remplissant une fonction de sécurité, ou dont la défaillance met en danger santé/sécurité des personnes ou des biens, art. 3 pt 14) ET relève-t-il des catégories de l'annexe I section A (machines, jouets, dispositifs médicaux, etc. — même liste que HR2) ? Si oui : haut risque et le fabricant est aussi considéré comme fournisseur. Sinon : reste « Product Manufacturer ».

## ai_act.S1 | S1 – Champ d'application territorial
mots-clés: utilisateurs européens UE Europe marché européen SaaS hors UE
source: art. 2
Dans le champ si : mise sur le marché / en service de systèmes d'IA dans l'UE (fournisseur) ; mise sur le marché de modèles d'IA à usage général (GPAI) dans l'UE (fournisseur → obligations GPAI, puis R1) ; établi ou situé dans l'UE (déployeur) ; établi dans l'UE et met sur le marché un système portant la marque d'un acteur hors UE (importateur) ; la sortie du système d'IA est utilisée dans l'UE (fournisseur, déployeur, distributeur). Aucun critère → hors champ (out of scope).

## ai_act.R1 | R1 – GPAI à risque systémique
mots-clés: LLM modèle de fondation GPT foundation model grand modèle de langage
source: art. 51
Un modèle GPAI présente un risque systémique s'il a des capacités à fort impact (calcul cumulé d'entraînement > 10^25 FLOP, art. 51 pt 2) ou si la Commission le décide selon l'annexe XIII. Alors : obligations « GPAI with Systemic Risk » (art. 55) en plus de celles des GPAI (art. 53). Puis R2.

## ai_act.R2 | R2 – Exclusions et exceptions
source: art. 2
- Usage exclusivement militaire : exclu, fin.
- Autorités/organisations internationales de pays tiers pour coopération policière/judiciaire : exclu, fin.
- Recherche et développement en IA : exclusion tant que non mis sur le marché/en service (uniquement R&D scientifique : exclu totalement) (art. 2 pts 6 et 8).
- Composants IA sous licence libre et open source : exclus tant qu'ils ne sont pas intégrés dans un système haut risque, interdit, à usage général ou soumis à transparence (art. 2 pt 12).
- Usage purement personnel non professionnel : obligations de déployeur non applicables (art. 2 pt 10).
- Système haut risque sous exception de l'art. 2 : seul l'art. 112 s'applique (revue par la Commission).
Puis R3.

## ai_act.R3 | R3 – Pratiques interdites
mots-clés: manipulation dark pattern scoring social notation citoyens surveillance de masse reconnaissance des émotions
source: art. 5
Le système est potentiellement INTERDIT s'il fait : techniques subliminales, manipulation et tromperie ; exploitation de vulnérabilités ; catégorisation biométrique ; notation sociale (social scoring) ; police prédictive ; extension de bases de reconnaissance faciale ; reconnaissance des émotions au travail ou en établissement d'enseignement (sauf raisons médicales/sécurité) ; biométrie à distance en temps réel. Statut « Prohibited ». Aucune → R4 (pour fournisseur/déployeur).

## ai_act.R4 | R4 – Obligations de transparence
mots-clés: chatbot assistant conversationnel IA générative LLM ChatGPT génération de texte image deepfake filigrane marquage synthétique
source: art. 50
- Interaction directe avec des personnes (fournisseur) → Transparency: Natural Persons (art. 50 pt 1) : informer qu'on interagit avec une IA.
- Génération de contenu synthétique audio/image/vidéo/texte (fournisseur) → Transparency: Synthetic Content (art. 50 pt 2) : marquage lisible par machine.
- Reconnaissance des émotions ou catégorisation biométrique (déployeur) → Transparency: Emotion & Biometric (art. 50 pt 3).
- Génération/manipulation d'image, audio, vidéo constituant un deepfake, ou de texte publié pour informer le public sur des sujets d'intérêt public (déployeur) → Transparency: Content Resemblance (art. 50 pt 4).
Si le système est aussi haut risque → continuer vers R5 (déployeur).

## ai_act.R5 | R5 – Analyse d'impact sur les droits fondamentaux (FRIA)
source: considérant 96, art. 27
Le déployeur d'un système à haut risque qui est un organisme de droit public ou une entité privée fournissant des services publics doit réaliser une analyse d'impact sur les droits fondamentaux avant déploiement (sauf infrastructures critiques). Sinon, fin du questionnaire.

## ai_act.obligations_entite | Obligations selon le type d'entité
source: art. 4, 16, 22, 23, 24, 26, considérants 47 et 166
- AI Literacy (art. 4) : fournisseurs et déployeurs doivent garantir un niveau suffisant de maîtrise de l'IA pour leur personnel et personnes opérant les systèmes, selon connaissances, expérience, formation et contexte.
- Handover (art. 25) : si un déployeur/distributeur/importateur modifie un système, il devient fournisseur ; l'ancien fournisseur doit lui transmettre informations, matériel et accès.
- Fournisseur d'un système haut risque : art. 16. Déployeur : art. 26. Distributeur : art. 24. Importateur : art. 23. Mandataire : art. 22 (haut risque) et/ou art. 54 (GPAI). Fabricant de produit : considérants 47 et 166 (+ fournisseur si haut risque, art. 25).

## ai_act.obligations_systeme | Obligations selon le type de système et statuts
source: art. 5, 6, 49, 50, 53, 55, 80, 99
- GPAI : obligations des fournisseurs de modèles à usage général (art. 53) ; obligations haut risque possibles indirectement (considérant 85).
- GPAI à risque systémique : art. 55.
- High risk : obligations du chapitre III section 2 selon le type d'entité.
- Notify NCA : fournisseur estimant son système non risqué (art. 6 pt 3) doit l'enregistrer dans la base UE avant mise sur le marché, documenter l'évaluation et la fournir aux autorités nationales sur demande. Si l'autorité juge le système mal classé (art. 80), obligations haut risque et amendes possibles (art. 99).
- Prohibited : art. 5. Out of scope : art. 2. Become a Provider : art. 25.
